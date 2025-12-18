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
from tribench.defaults import Defaults

logger = logging.getLogger(__name__)

# Default Kind cluster configuration path
DEFAULT_KIND_CONFIG = Path("config/kubernetes/kind-config.yaml")


class KubernetesSystem(System):
    """
    System implementation for Kubernetes-based deployments.
    
    Manages lifecycle using generated Kubernetes manifests applied via kubectl.
    Can also manage the Kind cluster itself (create/delete).
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Kubernetes system.
        
        Args:
            name: System name
            config: Configuration dictionary containing:
                - context: Kubernetes context name (default: Defaults.Kubernetes.CONTEXT)
                - namespace: Kubernetes namespace (default: Defaults.Kubernetes.NAMESPACE)
                - config_tree: The full configuration tree
                - kind_config: Path to Kind cluster config (default: config/kubernetes/kind-config.yaml)
        """
        super().__init__(name, config)
        self.context = config.get("context", Defaults.Kubernetes.CONTEXT)
        self.namespace = config.get("namespace", Defaults.Kubernetes.NAMESPACE)
        self.cluster_name = self.context.replace("kind-", "") if self.context.startswith("kind-") else "tribench"
        
        # Kind cluster configuration
        self.kind_config = Path(config.get("kind_config", DEFAULT_KIND_CONFIG))
        
        # Paths for generated manifests
        self.systems_path = Path("systems/kubernetes")
        self.trino_manifest = self.systems_path / "trino.yaml"
        self.minio_manifest = self.systems_path / "minio.yaml"
        self.postgres_manifest = self.systems_path / "postgres.yaml"
        self.hive_manifest = self.systems_path / "hive-metastore.yaml"
        
        # Port Forwarding
        self.local_port = config.get("local_port", Defaults.Trino.PORT)
        self.container_port = config.get("container_port", Defaults.Trino.PORT)
        self._pf_process: Optional[subprocess.Popen] = None
        
        # Timeout for operations in seconds
        self.timeout = config.get("timeout", Defaults.Timeouts.K8S_DEPLOYMENT)
        
        # Full config tree for generation
        self.config_tree = config.get("config_tree")
        
        # Initialize template engine
        from tribench.utils.config import ConfigurationTemplate
        self.template = ConfigurationTemplate()

    # =========================================================================
    # Kind Cluster Management
    # =========================================================================
    
    def cluster_exists(self) -> bool:
        """Check if the Kind cluster exists."""
        try:
            result = subprocess.run(
                ["kind", "get", "clusters"],
                capture_output=True,
                text=True,
                check=True
            )
            clusters = result.stdout.strip().split('\n')
            return self.cluster_name in clusters
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def cluster_status(self) -> Dict[str, Any]:
        """
        Get detailed cluster status.
        
        Returns:
            Dictionary with cluster info including nodes, their roles, and status
        """
        status = {
            "exists": False,
            "running": False,
            "nodes": [],
            "config_file": str(self.kind_config),
            "cluster_name": self.cluster_name,
        }
        
        if not self.cluster_exists():
            return status
        
        status["exists"] = True
        
        try:
            # Get node information
            result = subprocess.run(
                ["kubectl", "--context", self.context, "get", "nodes", "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            nodes_data = json.loads(result.stdout)
            
            for node in nodes_data.get("items", []):
                node_name = node["metadata"]["name"]
                labels = node["metadata"].get("labels", {})
                
                # Determine role from labels
                role = "worker"
                if "node-role.kubernetes.io/control-plane" in labels:
                    role = "control-plane"
                
                # Get status conditions
                conditions = node["status"].get("conditions", [])
                ready = any(c["type"] == "Ready" and c["status"] == "True" for c in conditions)
                
                status["nodes"].append({
                    "name": node_name,
                    "role": role,
                    "ready": ready,
                })
            
            # Cluster is running if we have nodes
            status["running"] = len(status["nodes"]) > 0 and all(n["ready"] for n in status["nodes"])
            
            # Compare with expected config
            if self.kind_config.exists():
                expected = self._parse_kind_config()
                status["expected_nodes"] = expected
                status["config_matches"] = self._config_matches(status["nodes"], expected)
            
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def _parse_kind_config(self) -> Dict[str, int]:
        """Parse Kind config to get expected node counts."""
        import yaml
        
        expected = {"control-plane": 0, "worker": 0}
        
        if not self.kind_config.exists():
            return expected
        
        try:
            with open(self.kind_config) as f:
                config = yaml.safe_load(f)
            
            for node in config.get("nodes", []):
                role = node.get("role", "worker")
                if role == "control-plane":
                    expected["control-plane"] += 1
                else:
                    expected["worker"] += 1
                    
        except Exception as e:
            logger.warning(f"Failed to parse Kind config: {e}")
        
        return expected
    
    def _config_matches(self, actual_nodes: List[Dict], expected: Dict[str, int]) -> bool:
        """Check if actual nodes match expected configuration."""
        actual_counts = {"control-plane": 0, "worker": 0}
        for node in actual_nodes:
            role = node.get("role", "worker")
            if role in actual_counts:
                actual_counts[role] += 1
        
        return actual_counts == expected
    
    def create_cluster(self, force: bool = False) -> bool:
        """
        Create the Kind cluster using the configuration file.
        
        Args:
            force: If True, delete existing cluster first
            
        Returns:
            True if cluster was created successfully
        """
        logger.info(f"Creating Kind cluster '{self.cluster_name}'...")
        
        # Check if cluster already exists
        if self.cluster_exists():
            if force:
                logger.info("Force flag set, deleting existing cluster...")
                self.delete_cluster()
            else:
                logger.warning(f"Cluster '{self.cluster_name}' already exists. Use force=True to recreate.")
                return False
        
        # Verify config file exists
        if not self.kind_config.exists():
            raise FileNotFoundError(f"Kind config file not found: {self.kind_config}")
        
        # Create cluster with config
        cmd = [
            "kind", "create", "cluster",
            "--name", self.cluster_name,
            "--config", str(self.kind_config)
        ]
        
        try:
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(result.stdout)
            logger.info(f"✓ Kind cluster '{self.cluster_name}' created successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create cluster: {e.stderr}")
            raise RuntimeError(f"Failed to create Kind cluster: {e.stderr}")
    
    def delete_cluster(self) -> bool:
        """
        Delete the Kind cluster.
        
        Returns:
            True if cluster was deleted successfully
        """
        logger.info(f"Deleting Kind cluster '{self.cluster_name}'...")
        
        if not self.cluster_exists():
            logger.info(f"Cluster '{self.cluster_name}' does not exist")
            return True
        
        # Stop port forwarding first
        self.stop_port_forwarding()
        
        cmd = ["kind", "delete", "cluster", "--name", self.cluster_name]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"✓ Kind cluster '{self.cluster_name}' deleted")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete cluster: {e.stderr}")
            raise RuntimeError(f"Failed to delete Kind cluster: {e.stderr}")
    
    def ensure_cluster(self) -> bool:
        """
        Ensure the Kind cluster exists and matches the expected configuration.
        
        If the cluster doesn't exist, creates it.
        If the cluster exists but doesn't match config, offers to recreate.
        
        Returns:
            True if cluster is ready
        """
        status = self.cluster_status()
        
        if not status["exists"]:
            logger.info("Cluster does not exist, creating...")
            return self.create_cluster()
        
        if not status.get("config_matches", True):
            expected = status.get("expected_nodes", {})
            actual_nodes = status.get("nodes", [])
            
            actual_counts = {"control-plane": 0, "worker": 0}
            for node in actual_nodes:
                role = node.get("role", "worker")
                if role in actual_counts:
                    actual_counts[role] += 1
            
            logger.warning(
                f"Cluster configuration mismatch:\n"
                f"  Expected: {expected['control-plane']} control-plane, {expected['worker']} worker nodes\n"
                f"  Actual: {actual_counts['control-plane']} control-plane, {actual_counts['worker']} worker nodes"
            )
            return False  # Return False to indicate mismatch - caller can decide to recreate
        
        logger.info(f"Cluster '{self.cluster_name}' exists and matches configuration")
        return True

    # =========================================================================
    # Original Methods
    # =========================================================================

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
        
        # Calculate worker count first
        workers_val = get_config_value(self.config_tree, "tribench.systems.trino.workers", 0)
        if isinstance(workers_val, list):
            worker_count = len(workers_val)
        else:
            worker_count = int(workers_val)

        # Auto-detect K8s worker nodes if config is 0
        if worker_count == 0:
            try:
                nodes_json = self._kubectl(["get", "nodes", "-o", "json"], namespace="")
                nodes = json.loads(nodes_json)
                # Count nodes that are NOT control-plane
                k8s_workers = 0
                for node in nodes.get("items", []):
                    labels = node["metadata"].get("labels", {})
                    if "node-role.kubernetes.io/control-plane" not in labels:
                        k8s_workers += 1
                
                if k8s_workers > 0:
                    logger.info(f"Auto-detected {k8s_workers} Kubernetes worker nodes. Setting Trino worker count to match.")
                    worker_count = k8s_workers
            except Exception as e:
                logger.warning(f"Failed to auto-detect K8s nodes: {e}")

        # Determine if coordinator should schedule work
        include_coordinator = worker_count == 0

        # 1. Generate Coordinator Configs
        # Use TrinoSystem to generate configs locally first
        trino_sys = TrinoSystem(config=self.config_tree)
        
        # Ensure directories exist and generate configs
        trino_sys._create_directories()
        trino_sys._generate_configs()
        
        # Read generated configs
        config_props = (trino_sys.install_path / "etc" / "config.properties").read_text()
        jvm_config = (trino_sys.install_path / "etc" / "jvm.config").read_text()
        node_props = (trino_sys.install_path / "etc" / "node.properties").read_text()
        
        # Append node-scheduler.include-coordinator if needed
        if not include_coordinator:
            config_props += "\nnode-scheduler.include-coordinator=false"

        # Read catalogs
        catalog_dir = trino_sys.install_path / "etc" / "catalog"
        catalogs = {}
        for cat_file in catalog_dir.glob("*.properties"):
            catalogs[cat_file.name] = cat_file.read_text()

        # 2. Generate Worker Configs
        # Clone config and override for worker
        worker_config = self.config_tree.copy()
        worker_config.put("tribench.systems.trino.coordinator.enabled", False)
        # Workers must point to the K8s service for discovery
        worker_config.put("tribench.systems.trino.coordinator.host", Defaults.ServiceNames.TRINO)
        
        trino_worker_sys = TrinoSystem(config=worker_config)
        trino_worker_sys._create_directories()
        trino_worker_sys._generate_configs()
        
        worker_config_props = (trino_worker_sys.install_path / "etc" / "config.properties").read_text()
        worker_jvm_config = (trino_worker_sys.install_path / "etc" / "jvm.config").read_text()
        worker_node_props = (trino_worker_sys.install_path / "etc" / "node.properties").read_text()
        
        # Remove node.id from worker_node_props to allow K8s/Trino to handle unique IDs for replicas
        worker_node_props = "\n".join([line for line in worker_node_props.splitlines() if not line.strip().startswith("node.id=")])
            
        # Build ConfigMap data for main config
        config_map_data = f"""
  config.properties: |
{self._indent(config_props, 4)}
  jvm.config: |
{self._indent(jvm_config, 4)}
  node.properties: |
{self._indent(node_props, 4)}
"""

        # Build ConfigMap data for worker config
        worker_config_map_data = f"""
  config.properties: |
{self._indent(worker_config_props, 4)}
  jvm.config: |
{self._indent(worker_jvm_config, 4)}
  node.properties: |
{self._indent(worker_node_props, 4)}
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
            worker_config_map_data=worker_config_map_data,
            catalog_map_data=catalog_map_data,
            worker_count=worker_count,
            include_coordinator=include_coordinator
        )

    def _generate_minio_manifest(self):
        """Generate MinIO manifest from MinIOSystem configuration."""
        logger.info(f"Generating MinIO manifest at {self.minio_manifest}")
        
        self.template.generate(
            template_name="k8s-minio.yaml.j2",
            config=self.config_tree,
            output_path=self.minio_manifest
        )

    def _ensure_minio_bucket(self, bucket_name: str) -> bool:
        """
        Ensure a bucket exists in MinIO.
        
        Creates the bucket directory inside the MinIO container's data directory.
        This is required for Hive Metastore to create schemas successfully.
        
        Args:
            bucket_name: Name of the bucket to create (e.g., 'warehouse')
            
        Returns:
            True if bucket exists or was created successfully
        """
        logger.info(f"Ensuring MinIO bucket '{bucket_name}' exists...")
        
        try:
            # Create bucket directory with proper permissions
            cmd = ["exec", "deployment/minio", "--", "sh", "-c", 
                   f"mkdir -p /data/{bucket_name} && chmod 777 /data/{bucket_name}"]
            self._kubectl(cmd)
            
            # Verify bucket was created
            result = self._kubectl(["exec", "deployment/minio", "--", "ls", "-d", f"/data/{bucket_name}"])
            if bucket_name in result:
                logger.info(f"✓ MinIO bucket '{bucket_name}' ready")
                return True
            else:
                logger.warning(f"Bucket '{bucket_name}' creation may have failed")
                return False
        except Exception as e:
            logger.error(f"Failed to create MinIO bucket '{bucket_name}': {e}")
            return False

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
        hive_sys.postgres_host = Defaults.ServiceNames.POSTGRESQL
        hive_sys.minio_endpoint = f"http://{Defaults.ServiceNames.MINIO}:{Defaults.MinIO.PORT}"
        
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
            
            # Create warehouse bucket for Iceberg/Hive
            self._ensure_minio_bucket("warehouse")

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
            # Always regenerate Trino manifest to ensure worker count matches current cluster
            # The worker count is auto-detected from K8s nodes, which may have changed
            logger.info(f"Generating fresh Trino manifest with current cluster state...")
            self._generate_trino_manifest()
            
            logger.info(f"Deploying Trino from {self.trino_manifest}")
            self._kubectl(["apply", "-f", str(self.trino_manifest)])
            self._kubectl(["rollout", "status", "deployment/trino-coordinator"])
            
            # Wait for workers if deployment exists
            try:
                self._kubectl(["rollout", "status", "deployment/trino-worker"], log_errors=False)
            except Exception:
                pass
            
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
                self._kubectl(["scale", "deployment", "trino-worker", "--replicas=0"], log_errors=False)
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
            result = sock.connect_ex((Defaults.Hosts.LOCALHOST, self.local_port))
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
        service_name = Defaults.ServiceNames.TRINO
        
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
            time.sleep(Defaults.Retry.PORT_FORWARD_STARTUP_DELAY)
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
                    time.sleep(Defaults.Retry.PROCESS_KILL_DELAY)
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
                    time.sleep(Defaults.Retry.PROCESS_KILL_DELAY)
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
