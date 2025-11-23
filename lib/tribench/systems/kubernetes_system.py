"""
Kubernetes system implementation for TriBench.

Manages system lifecycle on Kubernetes using Helm and kubectl.
"""

import logging
import subprocess
import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from tribench.core.system import System

from tribench.utils.config import get_config_value

logger = logging.getLogger(__name__)


class KubernetesSystem(System):
    """
    System implementation for Kubernetes-based deployments.
    
    Manages lifecycle using Helm charts and kubectl commands.
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
                - helm_chart: Chart name or path
                - helm_release: Release name
                - helm_values: Path to values.yaml
                - config_tree: The full configuration tree (optional, for generating values)
        """
        super().__init__(name, config)
        self.context = config.get("context", "kind-tribench")
        self.namespace = config.get("namespace", "tribench")
        self.helm_chart = config.get("helm_chart", "trinodb/trino")
        self.helm_release = config.get("helm_release", "tribench-trino")
        
        # Paths for generated values
        self.systems_path = Path("systems/kubernetes")
        self.helm_values = self.systems_path / "trino-values.yaml"
        self.minio_values = self.systems_path / "minio-values.yaml"
        self.postgres_values = self.systems_path / "postgres-values.yaml"
        self.hive_manifest = self.systems_path / "hive-metastore.yaml"
        
        # MinIO Configuration
        self.minio_chart = config.get("minio_chart", "bitnami/minio")
        self.minio_release = config.get("minio_release", "tribench-minio")
        
        # Port Forwarding
        self.local_port = config.get("local_port", 8080)
        self.container_port = config.get("container_port", 8080)
        self._pf_process: Optional[subprocess.Popen] = None
        
        # Timeout for operations in seconds
        self.timeout = config.get("timeout", 300)
        
        # Full config tree for generation
        self.config_tree = config.get("config_tree")

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

    def _helm(self, args: List[str], log_errors: bool = True) -> str:
        """Execute helm command."""
        cmd = ["helm", "--kube-context", self.context, "--namespace", self.namespace] + args
        return self._run_command(cmd, log_errors=log_errors).stdout.strip()

    def setup(self, component: str = "all") -> None:
        """
        Prepare Kubernetes environment.
        
        1. Verify cluster connection
        2. Create namespace
        3. Add Helm repositories
        4. Generate values.yaml files
        
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
        try:
            self._kubectl(["get", "namespace", self.namespace], namespace="")
        except subprocess.CalledProcessError:
            logger.info(f"Creating namespace '{self.namespace}'")
            self._kubectl(["create", "namespace", self.namespace], namespace="")

        # 3. Add Helm repos & Generate Values
        logger.info("Adding helm repos and generating configuration")
        
        # Trino Setup
        if component in ["all", "trino"]:
            if "trinodb" in self.helm_chart and not self.helm_chart.startswith("oci://"):
                self._helm(["repo", "add", "trinodb", "https://trinodb.github.io/charts"])
            
            # Generate Trino values
            self._generate_trino_values()
        
        # MinIO Setup
        if component in ["all", "minio"]:
            if "bitnami" in self.minio_chart and not self.minio_chart.startswith("oci://"):
                self._helm(["repo", "add", "bitnami", "https://charts.bitnami.com/bitnami"])
                
            if "minio" in self.minio_chart and "bitnami" not in self.minio_chart and not self.minio_chart.startswith("oci://"):
                 self._helm(["repo", "add", "minio", "https://charts.min.io/"])
            
            # Generate MinIO values
            self._generate_minio_values()

        # PostgreSQL Setup (for Hive Metastore)
        if component in ["all", "hive-metastore"]:
            self._helm(["repo", "add", "bitnami", "https://charts.bitnami.com/bitnami"])
            self._generate_postgres_values()
            self._generate_hive_metastore_manifest()
            self._build_and_load_hive_image()

        self._helm(["repo", "update"])

    def _generate_trino_values(self):
        """Generate Trino values.yaml from configuration."""
        logger.info(f"Generating Trino values at {self.helm_values}")
        
        # Defaults
        heap = "2G"
        version = "434"
        workers = 2
        
        if self.config_tree:
            heap = get_config_value(self.config_tree, "tribench.systems.trino.coordinator.jvm.heap", "2G")
            version = get_config_value(self.config_tree, "tribench.systems.trino.version", "434")
            # Allow configuring worker count for K8s specifically
            workers = get_config_value(self.config_tree, "tribench.systems.trino.k8s.workers", 2)
            
        # Basic values structure
        values = f"""
image:
  tag: "{version}"

server:
  workers: {workers}
  node:
    environment: tribench
  config:
    query:
      maxMemory: "4GB"
  jvm:
    maxHeapSize: "{heap}"
    gcMethodType: "G1"
    gcConifg:
      - "-XX:+UseG1GC"
      - "-XX:G1HeapRegionSize=32M"
      - "-XX:+ExplicitGCInvokesConcurrent"
      - "-XX:+ExitOnOutOfMemoryError"
      - "-Djdk.attach.allowAttachSelf=true"

coordinator:
  jvm:
    maxHeapSize: "{heap}"

worker:
  jvm:
    maxHeapSize: "{heap}"

# Catalogs
additionalCatalogs:
  tpch: |
    connector.name=tpch
    tpch.splits-per-node=4
  memory: |
    connector.name=memory
    memory.max-data-per-node=128MB
  iceberg: |
    connector.name=iceberg
    iceberg.catalog.type=hive_metastore
    hive.metastore.uri=thrift://tribench-hive-metastore:9083
    fs.native-s3.enabled=true
    s3.endpoint=http://tribench-minio:9000
    s3.aws-access-key=minioadmin
    s3.aws-secret-key=minioadmin
    s3.path-style-access=true
    s3.region=us-east-1
    iceberg.file-format=PARQUET
    iceberg.compression-codec=SNAPPY

service:
  type: ClusterIP
"""
        self.helm_values.write_text(values)

    def _generate_minio_values(self):
        """Generate MinIO values.yaml from configuration."""
        logger.info(f"Generating MinIO values at {self.minio_values}")
        
        # Defaults
        access_key = "minioadmin"
        secret_key = "minioadmin"
        
        if self.config_tree:
            access_key = get_config_value(self.config_tree, "tribench.systems.minio.access_key", "minioadmin")
            secret_key = get_config_value(self.config_tree, "tribench.systems.minio.secret_key", "minioadmin")
        
        values = f"""
mode: standalone
replicas: 1

image:
  tag: latest

auth:
  rootUser: {access_key}
  rootPassword: {secret_key}

resources:
  requests:
    memory: 256Mi
  limits:
    memory: 512Mi

persistence:
  enabled: false
  size: 10Gi
"""
        self.minio_values.write_text(values)

    def _generate_postgres_values(self):
        """Generate PostgreSQL values.yaml."""
        logger.info(f"Generating PostgreSQL values at {self.postgres_values}")
        
        # Defaults
        username = "hive"
        password = "hivepassword"
        database = "metastore"
        postgres_password = "postgrespassword"
        
        if self.config_tree:
            username = get_config_value(self.config_tree, "tribench.systems.postgresql.databases.metastore.user", username)
            password = get_config_value(self.config_tree, "tribench.systems.postgresql.databases.metastore.password", password)
            database = get_config_value(self.config_tree, "tribench.systems.postgresql.databases.metastore.name", database)
        
        values = f"""
auth:
  username: {username}
  password: {password}
  database: {database}
  postgresPassword: {postgres_password}

primary:
  persistence:
    enabled: false
  resources:
    requests:
      memory: 256Mi
    limits:
      memory: 512Mi
"""
        self.postgres_values.write_text(values)

    def _build_and_load_hive_image(self):
        """Build Hive Metastore image and load into Kind."""
        logger.info("Building and loading Hive Metastore image...")
        
        # Reuse HiveMetastoreSystem to generate Dockerfile
        from tribench.systems.hive_metastore import HiveMetastoreSystem
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
        
        # Special handling for Docker Desktop which might be using a Kind cluster named 'desktop'
        # or simply 'kind' but the context is 'docker-desktop'
        try:
            result = subprocess.run(["kind", "get", "clusters"], capture_output=True, text=True)
            if result.returncode == 0:
                clusters = result.stdout.strip().splitlines()
                if "desktop" in clusters and self.context == "docker-desktop":
                    return "desktop"
                # If there is exactly one cluster, assume it's the target
                if len(clusters) == 1:
                    return clusters[0]
        except FileNotFoundError:
            pass # kind not installed
            
        return None

    def _generate_hive_metastore_manifest(self):
        """Generate Kubernetes manifest for Hive Metastore."""
        logger.info(f"Generating Hive Metastore manifest at {self.hive_manifest}")
        
        # We need to generate the config files content to embed in ConfigMap
        from tribench.systems.hive_metastore import HiveMetastoreSystem
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
        
        manifest = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: hive-config
data:
  hive-site.xml: |
{self._indent(hive_site, 4)}
  core-site.xml: |
{self._indent(core_site, 4)}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hive-metastore
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hive-metastore
  template:
    metadata:
      labels:
        app: hive-metastore
    spec:
      containers:
      - name: metastore
        image: tribench-hive-metastore:{hive_sys.version}
        imagePullPolicy: Never
        ports:
        - containerPort: 9083
        env:
        - name: SERVICE_NAME
          value: metastore
        - name: DB_DRIVER
          value: postgres
        volumeMounts:
        - name: hive-config
          mountPath: /opt/hive/conf/hive-site.xml
          subPath: hive-site.xml
        - name: hive-config
          mountPath: /opt/hadoop/etc/hadoop/core-site.xml
          subPath: core-site.xml
      volumes:
      - name: hive-config
        configMap:
          name: hive-config
---
apiVersion: v1
kind: Service
metadata:
  name: tribench-hive-metastore
spec:
  selector:
    app: hive-metastore
  ports:
  - port: 9083
    targetPort: 9083
  type: ClusterIP
"""
        self.hive_manifest.write_text(manifest)

    def _indent(self, text: str, spaces: int) -> str:
        """Helper to indent text for YAML embedding."""
        return "\n".join(" " * spaces + line for line in text.splitlines())

    def start(self, component: str = "all") -> None:
        """
        Deploy system using Helm.
        
        Args:
            component: Component to start ('trino', 'minio', or 'all')
        """
        # 1. Install MinIO
        if component in ["all", "minio"]:
            logger.info(f"Installing MinIO via Helm release '{self.minio_release}'")
            
            if not self.minio_values.exists():
                logger.warning(f"MinIO values file not found at {self.minio_values}. Running setup...")
                self._generate_minio_values()

            minio_cmd = ["install", self.minio_release, self.minio_chart]
            minio_cmd.extend(["-f", str(self.minio_values)])
            minio_cmd.append("--wait") # Wait for MinIO to be ready
            
            try:
                self._helm(minio_cmd, log_errors=False)
            except subprocess.CalledProcessError as e:
                if "already exists" in e.stdout or "already exists" in e.stderr or "cannot reuse a name that is still in use" in e.stderr:
                    logger.warning(f"Release '{self.minio_release}' already exists")
                else:
                    # Log the error manually since we suppressed it
                    logger.error(f"Failed to install MinIO: {e.stderr}")
                    raise

        # 2. Install PostgreSQL (for Hive Metastore)
        if component in ["all", "hive-metastore"]:
            logger.info("Installing PostgreSQL...")
            if not self.postgres_values.exists():
                self._generate_postgres_values()
            
            pg_cmd = ["install", "tribench-postgresql", "bitnami/postgresql", "-f", str(self.postgres_values), "--wait"]
            try:
                self._helm(pg_cmd, log_errors=False)
            except subprocess.CalledProcessError as e:
                if "already exists" in e.stderr or "cannot reuse a name that is still in use" in e.stderr:
                    logger.warning("Release 'tribench-postgresql' already exists")
                else:
                    logger.error(f"Failed to install PostgreSQL: {e.stderr}")
                    raise

        # 3. Install Hive Metastore
        if component in ["all", "hive-metastore"]:
            logger.info("Installing Hive Metastore...")
            if not self.hive_manifest.exists():
                self._generate_hive_metastore_manifest()
            
            self._kubectl(["apply", "-f", str(self.hive_manifest)])
            # Wait for rollout
            self._kubectl(["rollout", "status", "deployment/hive-metastore"])

        # 4. Install Trino
        if component in ["all", "trino"]:
            logger.info(f"Starting system '{self.name}' via Helm release '{self.helm_release}'")
            
            if not self.helm_values.exists():
                logger.warning(f"Trino values file not found at {self.helm_values}. Running setup...")
                self._generate_trino_values()
            
            cmd = ["install", self.helm_release, self.helm_chart]
            cmd.extend(["-f", str(self.helm_values)])
                
            # Wait for readiness
            cmd.append("--wait")
            cmd.extend(["--timeout", f"{self.timeout}s"])
            
            try:
                self._helm(cmd, log_errors=False)
                self._is_running = True
                logger.info(f"System '{self.name}' started successfully")
                
                # 3. Start Port Forwarding
                self.start_port_forwarding()
                
            except subprocess.CalledProcessError as e:
                if "already exists" in e.stdout or "already exists" in e.stderr or "cannot reuse a name that is still in use" in e.stderr:
                    logger.warning(f"Release '{self.helm_release}' already exists")
                    self._is_running = True
                    self.start_port_forwarding()
                else:
                    # Log the error manually since we suppressed it
                    logger.error(f"Failed to start system '{self.name}': {e.stderr}")
                    raise

    def stop(self, component: str = "all") -> None:
        """
        Uninstall Helm releases and stop port forwarding.
        
        Args:
            component: Component to stop ('trino', 'minio', or 'all')
        """
        # 1. Stop Port Forwarding (only if stopping trino or all)
        if component in ["all", "trino"]:
            self.stop_port_forwarding()

            # 2. Uninstall Trino
            logger.info(f"Stopping system '{self.name}' (uninstalling release '{self.helm_release}')")
            try:
                self._helm(["uninstall", self.helm_release], log_errors=False)
                self._is_running = False
            except subprocess.CalledProcessError as e:
                if "not found" in e.stderr:
                    logger.warning(f"Release '{self.helm_release}' not found, already stopped?")
                    self._is_running = False
                else:
                    logger.warning(f"Error uninstalling Trino: {e}")
            
            # Cleanup lingering jobs
            try:
                self._kubectl(["delete", "jobs", "-l", f"release={self.helm_release}"], log_errors=False)
            except Exception:
                pass

        # 3. Uninstall MinIO
        if component in ["all", "minio"]:
            logger.info(f"Uninstalling MinIO release '{self.minio_release}'")
            try:
                self._helm(["uninstall", self.minio_release], log_errors=False)
            except subprocess.CalledProcessError as e:
                if "not found" in e.stderr:
                    pass
                else:
                    logger.warning(f"Error uninstalling MinIO: {e}")
            
            # Cleanup lingering jobs (Helm hooks)
            try:
                logger.debug(f"Cleaning up jobs for release '{self.minio_release}'")
                self._kubectl(["delete", "jobs", "-l", f"release={self.minio_release}"], log_errors=False)
            except Exception as e:
                logger.debug(f"Job cleanup failed (ignorable): {e}")

        # 4. Uninstall Hive Metastore & Postgres
        if component in ["all", "hive-metastore"]:
            logger.info("Uninstalling Hive Metastore and PostgreSQL")
            try:
                self._kubectl(["delete", "-f", str(self.hive_manifest)], log_errors=False)
            except Exception:
                pass
            
            try:
                self._helm(["uninstall", "tribench-postgresql"], log_errors=False)
            except Exception:
                pass

    def start_port_forwarding(self) -> None:
        """Start kubectl port-forward in the background."""
        # Clean up any existing forwarders first to avoid conflicts
        self.stop_port_forwarding()

        if self._pf_process and self._pf_process.poll() is None:
            logger.info("Port forwarding already running")
            return

        logger.info(f"Starting port forwarding {self.local_port}:{self.container_port}")
        
        # Find the service name
        service_name = self.helm_release
        try:
            self._kubectl(["get", "svc", service_name], log_errors=False)
        except subprocess.CalledProcessError:
            # Try with -trino suffix (common pattern)
            service_name = f"{self.helm_release}-trino"
            try:
                self._kubectl(["get", "svc", service_name], log_errors=False)
            except subprocess.CalledProcessError:
                # Fallback to release name and let it fail in the port-forward command
                service_name = self.helm_release
        
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
                start_new_session=True # Detach from parent
            )
            # Give it a moment to start
            time.sleep(2)
            if self._pf_process.poll() is not None:
                # It died immediately
                raise RuntimeError(f"Port forwarding failed to start. Check log/port-forward.log")
            
            logger.info(f"Port forwarding started for service '{service_name}' (pid {self._pf_process.pid})")
        except Exception as e:
            logger.error(f"Failed to start port forwarding: {e}")
            raise

    def stop_port_forwarding(self) -> None:
        """Stop the port forwarding process."""
        # Method 1: Stop the in-memory process (if this is the same session)
        if self._pf_process:
            logger.info("Stopping port forwarding (child process)")
            self._pf_process.terminate()
            try:
                self._pf_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._pf_process.kill()
            self._pf_process = None

        # Method 2: Find any process holding the port (for CLI statelessness)
        # This handles the case where the CLI exited but left kubectl running
        try:
            # Find PID using the port
            # lsof -t -i :8080 returns just the PID
            cmd = ["lsof", "-t", "-i", f":{self.local_port}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        logger.info(f"Killing zombie process {pid} on port {self.local_port}")
                        subprocess.run(["kill", pid], check=False)
        except Exception as e:
            # Don't fail if lsof isn't installed or fails
            logger.debug(f"Failed to check for zombie processes on port {self.local_port}: {e}")

    def teardown(self) -> None:
        """
        Clean up resources (delete namespace).
        """
        logger.info(f"Tearing down system '{self.name}'")
        self.stop()
        
        # Optional: Delete namespace? 
        # For now, we might want to keep it for debugging, but strictly teardown should clean up.
        # Let's leave namespace deletion manual or for a 'clean' command to avoid accidents.
        pass

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
                
                # Check if this is our Trino coordinator
                # Note: Helm release name is usually a prefix. 
                # Standard Trino chart creates {release}-trino-coordinator
                if self.helm_release in pod_name and "coordinator" in pod_name and pod_phase == "Running":
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
