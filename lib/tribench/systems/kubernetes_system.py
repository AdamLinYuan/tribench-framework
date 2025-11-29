"""
Kubernetes system implementation for TriBench.

Manages system lifecycle on Kubernetes using native manifests generated from
Docker system definitions, bypassing Helm charts for simplicity and consistency.
"""

import logging
import os
import signal
import subprocess
import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from tribench.core.system import System
from tribench.systems.minio import MinIOSystem
from tribench.systems.trino import TrinoSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.utils.config import get_config_value

logger = logging.getLogger(__name__)


class KubernetesSystem(System):
    """
    System implementation for Kubernetes-based deployments.
    
    Manages lifecycle using generated Kubernetes manifests applied via kubectl.
    Assumes a Kubernetes cluster (like kind) is already running and configured
    in the local kubeconfig.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Kubernetes system.
        
        Args:
            name: System name
            config: Configuration dictionary containing:
                - context: Kubernetes context name (default: kind-tribench)
                - namespace: Kubernetes namespace (default: tribench)
                - config_tree: The full configuration tree
        """
        super().__init__(name, config)
        self.context = config.get("context", "kind-tribench")
        self.namespace = config.get("namespace", "tribench")
        
        # Paths for generated manifests
        self.systems_path = Path("systems/kubernetes")
        self.trino_manifest = self.systems_path / "trino.yaml"
        self.minio_manifest = self.systems_path / "minio.yaml"
        self.postgres_manifest = self.systems_path / "postgres.yaml"
        self.hive_manifest = self.systems_path / "hive-metastore.yaml"
        
        # Port Forwarding
        self.local_port = config.get("local_port", 8080)
        self.container_port = config.get("container_port", 8080)
        self._pf_process: Optional[subprocess.Popen] = None
        
        # Timeout for operations in seconds
        self.timeout = config.get("timeout", 300)
        
        # Full config tree for generation
        self.config_tree = config.get("config_tree")
        
        # Initialize template engine
        from tribench.utils.config import ConfigurationTemplate
        self.template = ConfigurationTemplate()

    def _run_command(self, cmd: List[str], check: bool = True, capture: bool = True, log_errors: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            if log_errors:
                logger.error(f"Command failed: {' '.join(cmd)}")
                if capture:
                    logger.error(f"Stdout: {e.stdout}")
                    logger.error(f"Stderr: {e.stderr}")
            raise

    def _kubectl(self, args: List[str], namespace: Optional[str] = None, log_errors: bool = True) -> str:
        """Execute kubectl command."""
        cmd = ["kubectl", "--context", self.context]
        
        # Use configured namespace unless explicitly overridden or set to None (cluster-wide)
        ns = namespace if namespace is not None else self.namespace
        if ns:
            cmd.extend(["--namespace", ns])
            
        cmd.extend(args)
        return self._run_command(cmd, log_errors=log_errors).stdout.strip()

    def _ensure_namespace(self) -> None:
        """Ensure the configured namespace exists."""
        try:
            self._kubectl(["get", "namespace", self.namespace], namespace="")
        except subprocess.CalledProcessError:
            logger.info(f"Creating namespace '{self.namespace}'")
            self._kubectl(["create", "namespace", self.namespace], namespace="")

    def setup(self, component: str = "all") -> None:
        """
        Prepare Kubernetes environment.
        
        1. Verify cluster connection
        2. Create namespace
        3. Generate Kubernetes manifests
        
        Args:
            component: Component to setup ('trino', 'minio', or 'all')
        """
        logger.info(f"Setting up Kubernetes system '{self.name}' in namespace '{self.namespace}' for component '{component}'")
        
        # Create systems directory if it doesn't exist
        self.systems_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Verify connection
        try:
            self._kubectl(["cluster-info"], namespace="")
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Cannot connect to Kubernetes cluster with context '{self.context}'")

        # 2. Create namespace if not exists
        self._ensure_namespace()

        # 3. Generate Manifests
        logger.info("Generating Kubernetes manifests")
        
        # Trino Setup
        if component in ["all", "trino"]:
            self._generate_trino_manifest()
        
        # MinIO Setup
        if component in ["all", "minio"]:
            self._generate_minio_manifest()

        # PostgreSQL & Hive Metastore Setup
        if component in ["all", "hive-metastore"]:
            self._generate_postgres_manifest()
            self._load_postgres_image()
            self._generate_hive_metastore_manifest()
            self._build_and_load_hive_image()

    def _load_postgres_image(self):
        """Pull PostgreSQL image and load into Kind."""
        image = "postgres:13"
        cluster_name = self._get_kind_cluster_name()
        
        if cluster_name:
            logger.info(f"Loading {image} into Kind cluster '{cluster_name}'...")
            try:
                # Pull locally first
                subprocess.run(["docker", "pull", image], check=True)
                
                # Try loading via archive which is often more robust for multi-arch
                archive_path = Path("postgres-13.tar")
                logger.info(f"Saving {image} to {archive_path}...")
                subprocess.run(["docker", "save", "-o", str(archive_path), image], check=True)
                
                logger.info(f"Loading archive into Kind...")
                subprocess.run(
                    ["kind", "load", "image-archive", str(archive_path), "--name", cluster_name],
                    check=True
                )
                
                # Clean up
                if archive_path.exists():
                    archive_path.unlink()
                    
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to load image {image} into Kind: {e}")
                logger.warning("Will proceed, hoping the nodes can pull it or it loaded partially.")
                # Clean up in case of error
                if Path("postgres-13.tar").exists():
                    Path("postgres-13.tar").unlink()
        else:
            logger.info(f"Skipping kind load for {image} (not identified as a Kind cluster)")

    def _generate_trino_manifest(self):
        """Generate Trino manifest from TrinoSystem configuration."""
        logger.info(f"Generating Trino manifest at {self.trino_manifest}")
        
        # Use TrinoSystem to generate configs locally first
        trino_sys = TrinoSystem(config=self.config_tree)
        
        # Ensure directories exist and generate configs
        trino_sys._create_directories()
        trino_sys._generate_configs()
        
        # Read generated configs
        config_props = (trino_sys.install_path / "etc" / "config.properties").read_text()
        jvm_config = (trino_sys.install_path / "etc" / "jvm.config").read_text()
        node_props = (trino_sys.install_path / "etc" / "node.properties").read_text()
        
        # Read catalogs
        catalog_dir = trino_sys.install_path / "etc" / "catalog"
        catalogs = {}
        for cat_file in catalog_dir.glob("*.properties"):
            catalogs[cat_file.name] = cat_file.read_text()
            
        # Build ConfigMap data for main config
        config_map_data = f"""
  config.properties: |
{self._indent(config_props, 4)}
  jvm.config: |
{self._indent(jvm_config, 4)}
  node.properties: |
{self._indent(node_props, 4)}
"""
        
        # Build ConfigMap data for catalogs
        catalog_map_data = ""
        for name, content in catalogs.items():
            catalog_map_data += f"""
  {name}: |
{self._indent(content, 4)}
"""

        self.template.generate(
            template_name="k8s-trino.yaml.j2",
            config=self.config_tree,
            output_path=self.trino_manifest,
            config_map_data=config_map_data,
            catalog_map_data=catalog_map_data
        )

    def _generate_minio_manifest(self):
        """Generate MinIO manifest from MinIOSystem configuration."""
        logger.info(f"Generating MinIO manifest at {self.minio_manifest}")
        
        self.template.generate(
            template_name="k8s-minio.yaml.j2",
            config=self.config_tree,
            output_path=self.minio_manifest
        )

    def _generate_postgres_manifest(self):
        """Generate PostgreSQL manifest."""
        logger.info(f"Generating PostgreSQL manifest at {self.postgres_manifest}")
        
        self.template.generate(
            template_name="k8s-postgres.yaml.j2",
            config=self.config_tree,
            output_path=self.postgres_manifest
        )

    def _build_and_load_hive_image(self):
        """Build Hive Metastore image and load into Kind."""
        logger.info("Building and loading Hive Metastore image...")
        
        hive_sys = HiveMetastoreSystem(config=self.config_tree if self.config_tree else {})
        
        # Ensure directories exist
        hive_sys.system_dir.mkdir(parents=True, exist_ok=True)
        hive_sys._generate_dockerfile()
        
        image_tag = f"tribench-hive-metastore:{hive_sys.version}"
        
        # Build
        logger.info(f"Building Docker image {image_tag}...")
        subprocess.run(
            ["docker", "build", "-t", image_tag, "."],
            cwd=hive_sys.system_dir,
            check=True
        )
        
        # Load into Kind
        cluster_name = self._get_kind_cluster_name()
        if cluster_name:
            logger.info(f"Loading image into Kind cluster '{cluster_name}'...")
            subprocess.run(
                ["kind", "load", "docker-image", image_tag, "--name", cluster_name],
                check=True
            )
        else:
            logger.info(f"Skipping kind load for context '{self.context}' (not identified as a Kind cluster)")

    def _get_kind_cluster_name(self) -> Optional[str]:
        """Determine the Kind cluster name from the current context."""
        if self.context.startswith("kind-"):
            return self.context.replace("kind-", "")
        
        try:
            result = subprocess.run(["kind", "get", "clusters"], capture_output=True, text=True)
            if result.returncode == 0:
                clusters = result.stdout.strip().splitlines()
                if "desktop" in clusters and self.context == "docker-desktop":
                    return "desktop"
                if len(clusters) == 1:
                    return clusters[0]
        except FileNotFoundError:
            pass 
            
        return None

    def _generate_hive_metastore_manifest(self):
        """Generate Kubernetes manifest for Hive Metastore."""
        logger.info(f"Generating Hive Metastore manifest at {self.hive_manifest}")
        
        hive_sys = HiveMetastoreSystem(config=self.config_tree if self.config_tree else {})
        
        # Temporarily generate configs to read them
        hive_sys.conf_dir.mkdir(parents=True, exist_ok=True)
        
        # Override hostnames for K8s DNS
        hive_sys.postgres_host = "tribench-postgresql"
        hive_sys.minio_endpoint = "http://tribench-minio:9000"
        
        hive_sys._generate_metastore_site()
        hive_sys._generate_core_site()
        
        hive_site = (hive_sys.conf_dir / "hive-site.xml").read_text()
        core_site = (hive_sys.conf_dir / "core-site.xml").read_text()
        
        self.template.generate(
            template_name="k8s-hive.yaml.j2",
            config=self.config_tree,
            output_path=self.hive_manifest,
            hive_site=hive_site,
            core_site=core_site
        )

    def _indent(self, text: str, spaces: int) -> str:
        """Helper to indent text for YAML embedding."""
        return "\n".join(" " * spaces + line for line in text.splitlines())

    def start(self, component: str = "all") -> None:
        """
        Deploy system using generated manifests.
        
        Args:
            component: Component to start ('trino', 'minio', or 'all')
        """
        # Ensure namespace exists before starting
        self._ensure_namespace()

        # 1. Install MinIO
        if component in ["all", "minio"]:
            logger.info(f"Deploying MinIO from {self.minio_manifest}")
            if not self.minio_manifest.exists():
                self._generate_minio_manifest()
            
            self._kubectl(["apply", "-f", str(self.minio_manifest)])
            self._kubectl(["rollout", "status", "deployment/minio"])

        # 2. Install PostgreSQL (for Hive Metastore)
        if component in ["all", "hive-metastore"]:
            logger.info("Deploying PostgreSQL...")
            if not self.postgres_manifest.exists():
                self._generate_postgres_manifest()
            
            self._kubectl(["apply", "-f", str(self.postgres_manifest)])
            self._kubectl(["rollout", "status", "deployment/postgresql"])

        # 3. Install Hive Metastore
        if component in ["all", "hive-metastore"]:
            logger.info("Deploying Hive Metastore...")
            if not self.hive_manifest.exists():
                self._generate_hive_metastore_manifest()
            
            self._kubectl(["apply", "-f", str(self.hive_manifest)])
            self._kubectl(["rollout", "status", "deployment/hive-metastore"])

        # 4. Install Trino
        if component in ["all", "trino"]:
            logger.info(f"Deploying Trino from {self.trino_manifest}")
            if not self.trino_manifest.exists():
                self._generate_trino_manifest()
            
            self._kubectl(["apply", "-f", str(self.trino_manifest)])
            self._kubectl(["rollout", "status", "deployment/trino-coordinator"])
            
            self._is_running = True
            logger.info(f"System '{self.name}' started successfully")
            
            # Start Port Forwarding
            self.start_port_forwarding()

    def stop(self, component: str = "all") -> None:
        """
        Stop systems by scaling deployments to 0.
        
        Args:
            component: Component to stop ('trino', 'minio', or 'all')
        """
        # 1. Stop Port Forwarding (only if stopping trino or all)
        if component in ["all", "trino"]:
            self.stop_port_forwarding()

            # 2. Stop Trino
            logger.info(f"Stopping Trino (scaling to 0)...")
            try:
                self._kubectl(["scale", "deployment", "trino-coordinator", "--replicas=0"], log_errors=False)
                self._is_running = False
            except Exception:
                pass

        # 3. Stop MinIO
        if component in ["all", "minio"]:
            logger.info(f"Stopping MinIO (scaling to 0)...")
            try:
                self._kubectl(["scale", "deployment", "minio", "--replicas=0"], log_errors=False)
            except Exception:
                pass

        # 4. Stop Hive Metastore & Postgres
        if component in ["all", "hive-metastore"]:
            logger.info("Stopping Hive Metastore and PostgreSQL (scaling to 0)...")
            try:
                self._kubectl(["scale", "deployment", "hive-metastore", "--replicas=0"], log_errors=False)
            except Exception:
                pass
            
            try:
                self._kubectl(["scale", "deployment", "postgresql", "--replicas=0"], log_errors=False)
            except Exception:
                pass

    def teardown(self, component: str = "all") -> None:
        """
        Uninstall systems by deleting resources.
        
        Args:
            component: Component to teardown ('trino', 'minio', or 'all')
        """
        logger.info(f"Tearing down system '{self.name}' (component: {component})")
        
        # Stop port forwarding first
        self.stop_port_forwarding()

        # 1. Uninstall Trino
        if component in ["all", "trino"]:
            logger.info(f"Deleting Trino resources...")
            try:
                self._kubectl(["delete", "-f", str(self.trino_manifest)], log_errors=False)
                self._is_running = False
            except Exception:
                pass

        # 2. Uninstall MinIO
        if component in ["all", "minio"]:
            logger.info(f"Deleting MinIO resources...")
            try:
                self._kubectl(["delete", "-f", str(self.minio_manifest)], log_errors=False)
            except Exception:
                pass

        # 3. Uninstall Hive Metastore & Postgres
        if component in ["all", "hive-metastore"]:
            logger.info("Deleting Hive Metastore and PostgreSQL resources...")
            try:
                self._kubectl(["delete", "-f", str(self.hive_manifest)], log_errors=False)
            except Exception:
                pass
            
            try:
                self._kubectl(["delete", "-f", str(self.postgres_manifest)], log_errors=False)
            except Exception:
                pass

    def is_port_forwarding_active(self) -> bool:
        """Check if port forwarding is currently active."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', self.local_port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def ensure_port_forwarding(self) -> bool:
        """
        Ensure port forwarding is active, starting it if necessary.
        
        Returns:
            True if port forwarding is now active, False otherwise
        """
        if self.is_port_forwarding_active():
            logger.info(f"Port forwarding already active on port {self.local_port}")
            return True
        
        # Check if Trino is running in K8s before trying to forward
        status = self.status()
        if not status.get("running"):
            logger.warning("Trino is not running in Kubernetes. Start it first with 'tribench sys start trino --kind'")
            return False
        
        logger.info("Port forwarding not active, starting...")
        self.start_port_forwarding()
        return self.is_port_forwarding_active()

    def start_port_forwarding(self) -> None:
        """Start kubectl port-forward in the background and persist PID."""
        # Check if already running (from PID file or active process)
        if self.is_port_forwarding_active():
            logger.info("Port forwarding already active")
            return

        # Clean up any stale processes
        self._cleanup_stale_port_forward()

        logger.info(f"Starting port forwarding {self.local_port}:{self.container_port}")
        
        # Service name is now fixed in our manifests
        service_name = "tribench-trino"
        
        cmd = [
            "kubectl", "--context", self.context, "--namespace", self.namespace,
            "port-forward", f"svc/{service_name}", 
            f"{self.local_port}:{self.container_port}"
        ]
        
        # Ensure log directory exists
        Path("log").mkdir(exist_ok=True)
        pf_log = open("log/port-forward.log", "w")
        
        try:
            self._pf_process = subprocess.Popen(
                cmd,
                stdout=pf_log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True  # Detach from parent
            )
            # Give it a moment to start
            time.sleep(2)
            if self._pf_process.poll() is not None:
                # It died immediately
                raise RuntimeError(f"Port forwarding failed to start. Check log/port-forward.log")
            
            # Persist PID to file for cross-session access
            pid_file = Path("log/port-forward.pid")
            pid_file.write_text(str(self._pf_process.pid))
            
            logger.info(f"Port forwarding started for service '{service_name}' (pid {self._pf_process.pid})")
        except Exception as e:
            logger.error(f"Failed to start port forwarding: {e}")
            raise

    def _cleanup_stale_port_forward(self) -> None:
        """Clean up any stale port forwarding processes."""
        pid_file = Path("log/port-forward.pid")
        
        # Try to kill process from PID file
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                # Check if process is still running
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    logger.info(f"Killing stale port-forward process {pid}")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, signal.SIGKILL)  # Force kill if still alive
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass  # Process already dead
                pid_file.unlink()
            except (ValueError, OSError) as e:
                logger.debug(f"Could not clean up from PID file: {e}")
                pid_file.unlink(missing_ok=True)

    def stop_port_forwarding(self) -> None:
        """Stop the port forwarding process."""
        # Method 1: Stop from PID file (cross-session)
        pid_file = Path("log/port-forward.pid")
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                logger.info(f"Stopping port forwarding (pid {pid})")
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    logger.debug(f"Process {pid} already dead")
                pid_file.unlink()
            except (ValueError, OSError) as e:
                logger.debug(f"Could not stop from PID file: {e}")
                pid_file.unlink(missing_ok=True)
        
        # Method 2: Stop the in-memory process (if this is the same session)
        if self._pf_process:
            logger.info("Stopping port forwarding (child process)")
            self._pf_process.terminate()
            try:
                self._pf_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._pf_process.kill()
            self._pf_process = None

        # Method 3: Find any process holding the port (fallback)
        try:
            cmd = ["lsof", "-t", "-i", f":{self.local_port}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        logger.info(f"Killing process {pid} on port {self.local_port}")
                        subprocess.run(["kill", pid], check=False)
        except Exception as e:
            logger.debug(f"Failed to check for processes on port {self.local_port}: {e}")

    def status(self) -> Dict[str, Any]:
        """
        Get system status from Kubernetes.
        """
        status = {
            "running": False,
            "pods": [],
            "services": []
        }
        
        try:
            # Get Pods
            pods_json = self._kubectl(["get", "pods", "-o", "json"])
            pods = json.loads(pods_json)
            
            trino_running = False
            
            for pod in pods.get("items", []):
                pod_name = pod["metadata"]["name"]
                pod_phase = pod["status"]["phase"]
                is_ready = all(c["ready"] for c in pod["status"].get("containerStatuses", []))
                
                status["pods"].append({
                    "name": pod_name,
                    "status": pod_phase,
                    "ready": is_ready
                })
                
                if "trino" in pod_name and pod_phase == "Running":
                    trino_running = True

            # Get Services
            svc_json = self._kubectl(["get", "svc", "-o", "json"])
            svcs = json.loads(svc_json)
            for svc in svcs.get("items", []):
                status["services"].append({
                    "name": svc["metadata"]["name"],
                    "type": svc["spec"]["type"],
                    "ports": svc["spec"]["ports"]
                })
            
            status["running"] = trino_running
            self._is_running = trino_running
                
        except Exception as e:
            status["error"] = str(e)
            
        return status
