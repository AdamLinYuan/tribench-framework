"""
Kubernetes system implementation.

Manages system lifecycle on Kubernetes using native manifests.
"""

import logging
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

from tribench.core.system import System
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.defaults import Defaults

from .cluster import KindClusterManager
from .kubectl import KubectlOperator
from .manifests import ManifestGenerator
from .port_forward import PortForwarder

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
            config: Configuration dictionary (includes systems.kubernetes settings)
        """
        super().__init__(name, config)
        
        # Use config hierarchy for context and namespace
        self.context = Defaults.Kubernetes.get_context(config)
        self.namespace = Defaults.Kubernetes.get_namespace(config)
        
        logger.info(f"Kubernetes context: {self.context}")
        logger.info(f"Kubernetes namespace: {self.namespace}")
        
        self.cluster_name = self.context.replace("kind-", "") if self.context.startswith("kind-") else "tribench"
        
        # Paths for generated manifests
        self.systems_path = Path("systems/kubernetes")
        self.trino_manifest = self.systems_path / "trino.yaml"
        self.minio_manifest = self.systems_path / "minio.yaml"
        self.postgres_manifest = self.systems_path / "postgres.yaml"
        self.hive_manifest = self.systems_path / "hive-metastore.yaml"
        
        # Configuration
        self.kind_config = Path(config.get("kind_config", DEFAULT_KIND_CONFIG))
        self.local_port = config.get("local_port", Defaults.Trino.PORT)
        self.container_port = config.get("container_port", Defaults.Trino.PORT)
        self.timeout = config.get("timeout", Defaults.Timeouts.K8S_DEPLOYMENT)
        self.config_tree = config.get("config_tree")
        
        # Initialize components
        self.cluster = KindClusterManager(self.cluster_name, self.context, self.kind_config)
        self.kubectl = KubectlOperator(self.context, self.namespace)
        self.manifests = ManifestGenerator(self.config_tree, self.context, self.namespace)
        self.port_forwarder = PortForwarder(self.context, self.namespace, self.local_port, self.container_port)
        
        # MinIO port forwarder (separate process for multiple ports)
        self.minio_port_forwarder = PortForwarder(
            self.context, 
            self.namespace, 
            Defaults.MinIO.PORT, 
            Defaults.MinIO.PORT
        )
        # Update PID/log file names to avoid conflicts
        self.minio_port_forwarder.pid_file = Path("log/port-forward-minio.pid")
        self.minio_port_forwarder.log_file = Path("log/port-forward-minio.log")
    
    # ========== Kind Cluster Management ==========
    
    def cluster_exists(self) -> bool:
        """Check if the Kind cluster exists."""
        return self.cluster.exists()
    
    def cluster_status(self) -> Dict[str, Any]:
        """Get detailed cluster status."""
        return self.cluster.status()
    
    def create_cluster(self, force: bool = False) -> bool:
        """Create the Kind cluster."""
        return self.cluster.create(force)
    
    def delete_cluster(self) -> bool:
        """Delete the Kind cluster."""
        self.stop_port_forwarding()
        return self.cluster.delete()
    
    def ensure_cluster(self) -> bool:
        """Ensure the Kind cluster exists and matches configuration."""
        return self.cluster.ensure()
    
    def install_metrics_server(self, force: bool = False) -> bool:
        """
        Install metrics-server for Kubernetes pod monitoring.
        
        Args:
            force: Force reinstall even if already installed
            
        Returns:
            True if installation successful, False otherwise
        """
        logger.info("Installing metrics-server for Kubernetes monitoring...")
        
        try:
            # Check if metrics-server is already installed
            if not force:
                result = subprocess.run(
                    ["kubectl", "--context", self.context, "-n", "kube-system",
                     "get", "deployment", "metrics-server"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info("metrics-server already installed")
                    return True
            
            # Install metrics-server from official release
            logger.info("Applying metrics-server manifests...")
            result = subprocess.run(
                ["kubectl", "--context", self.context, "apply", "-f",
                 "https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to apply metrics-server manifests: {result.stderr}")
                return False
            
            # For Kind clusters, patch metrics-server to use insecure TLS
            # (Kind uses self-signed certificates)
            if self.context.startswith("kind-"):
                logger.info("Patching metrics-server for Kind (insecure TLS)...")
                result = subprocess.run(
                    ["kubectl", "--context", self.context, "-n", "kube-system",
                     "patch", "deployment", "metrics-server", "--type=json",
                     "-p", '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    logger.warning(f"Failed to patch metrics-server: {result.stderr}")
            
            # Wait for metrics-server to be ready
            logger.info("Waiting for metrics-server to be ready...")
            result = subprocess.run(
                ["kubectl", "--context", self.context, "-n", "kube-system",
                 "wait", "--for=condition=ready", "pod", "-l", "k8s-app=metrics-server",
                 "--timeout=60s"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✓ metrics-server installed and ready")
                return True
            else:
                logger.warning(f"metrics-server may not be fully ready: {result.stderr}")
                return True  # Still return True as it was installed
                
        except subprocess.TimeoutExpired:
            logger.warning("Timeout installing metrics-server, but it may still be initializing")
            return True
        except Exception as e:
            logger.error(f"Error installing metrics-server: {e}")
            return False
    
    # ========== Setup and Manifest Generation ==========
    
    def setup(self, component: str = "all") -> None:
        """
        Prepare Kubernetes environment.
        
        Args:
            component: Component to setup ('trino', 'minio', 'hive-metastore', or 'all')
        """
        logger.info(f"Setting up Kubernetes system '{self.name}' in namespace '{self.namespace}' for component '{component}'")
        
        # Create systems directory
        self.systems_path.mkdir(parents=True, exist_ok=True)
        
        # Verify connection
        self.kubectl.verify_cluster()
        
        # Create namespace
        self.kubectl.ensure_namespace()
        
        # Generate manifests
        logger.info("Generating Kubernetes manifests")
        
        if component in ["all", "trino"]:
            self.manifests.generate_trino(self.trino_manifest)
        
        if component in ["all", "minio"]:
            self.manifests.generate_minio(self.minio_manifest)
        
        if component in ["all", "hive-metastore"]:
            self.manifests.generate_postgres(self.postgres_manifest)
            self._load_postgres_image()
            self.manifests.generate_hive_metastore(self.hive_manifest)
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
                
                # Save and load via archive
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
                # Clean up in case of error
                if Path("postgres-13.tar").exists():
                    Path("postgres-13.tar").unlink()
        else:
            logger.info(f"Skipping kind load for {image} (not identified as a Kind cluster)")
    
    def _build_and_load_hive_image(self):
        """Build Hive Metastore image and load into Kind."""
        logger.info("Building and loading Hive Metastore image...")
        
        hive_sys = HiveMetastoreSystem(config=self.config_tree if self.config_tree else {})
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
    
    # ========== Deployment Management ==========
    
    def start(self, component: str = "all") -> None:
        """
        Deploy system using generated manifests.
        
        Args:
            component: Component to start ('trino', 'minio', 'hive-metastore', or 'all')
        """
        self.kubectl.ensure_namespace()
        
        # Deploy MinIO
        if component in ["all", "minio"]:
            logger.info(f"Deploying MinIO from {self.minio_manifest}")
            if not self.minio_manifest.exists():
                self.manifests.generate_minio(self.minio_manifest)
            
            self.kubectl.apply_manifest(self.minio_manifest)
            self.kubectl.wait_for_rollout("deployment/minio")
            self.kubectl.ensure_bucket("minio", "warehouse")
        
        # Deploy PostgreSQL
        if component in ["all", "hive-metastore"]:
            logger.info("Deploying PostgreSQL...")
            if not self.postgres_manifest.exists():
                self.manifests.generate_postgres(self.postgres_manifest)
            
            self.kubectl.apply_manifest(self.postgres_manifest)
            self.kubectl.wait_for_rollout("deployment/postgresql")
        
        # Deploy Hive Metastore
        if component in ["all", "hive-metastore"]:
            logger.info("Deploying Hive Metastore...")
            if not self.hive_manifest.exists():
                self.manifests.generate_hive_metastore(self.hive_manifest)
            
            self.kubectl.apply_manifest(self.hive_manifest)
            self.kubectl.wait_for_rollout("deployment/hive-metastore")
        
        # Deploy Trino
        if component in ["all", "trino"]:
            logger.info(f"Generating fresh Trino manifest with current cluster state...")
            self.manifests.generate_trino(self.trino_manifest)
            
            logger.info(f"Deploying Trino from {self.trino_manifest}")
            self.kubectl.apply_manifest(self.trino_manifest)
            self.kubectl.wait_for_rollout("deployment/trino-coordinator")
            self.kubectl.wait_for_rollout("deployment/trino-worker", log_errors=False)
            
            self._is_running = True
            logger.info(f"System '{self.name}' started successfully")
            self.start_port_forwarding()
    
    def stop(self, component: str = "all") -> None:
        """
        Stop systems by scaling deployments to 0.
        
        Args:
            component: Component to stop
        """
        if component in ["all", "trino"]:
            self.stop_port_forwarding()
            logger.info(f"Stopping Trino (scaling to 0)...")
            self.kubectl.scale_deployment("trino-coordinator", 0, log_errors=False)
            self.kubectl.scale_deployment("trino-worker", 0, log_errors=False)
            self._is_running = False
        
        if component in ["all", "minio"]:
            logger.info(f"Stopping MinIO (scaling to 0)...")
            self.kubectl.scale_deployment("minio", 0, log_errors=False)
        
        if component in ["all", "hive-metastore"]:
            logger.info("Stopping Hive Metastore and PostgreSQL (scaling to 0)...")
            self.kubectl.scale_deployment("hive-metastore", 0, log_errors=False)
            self.kubectl.scale_deployment("postgresql", 0, log_errors=False)
    
    def teardown(self, component: str = "all") -> None:
        """
        Uninstall systems by deleting resources.
        
        Args:
            component: Component to teardown
        """
        logger.info(f"Tearing down system '{self.name}' (component: {component})")
        
        self.stop_port_forwarding()
        
        if component in ["all", "trino"]:
            logger.info(f"Deleting Trino resources...")
            self.kubectl.delete_manifest(self.trino_manifest, log_errors=False)
            self._is_running = False
        
        if component in ["all", "minio"]:
            logger.info(f"Deleting MinIO resources...")
            self.kubectl.delete_manifest(self.minio_manifest, log_errors=False)
        
        if component in ["all", "hive-metastore"]:
            logger.info("Deleting Hive Metastore and PostgreSQL resources...")
            self.kubectl.delete_manifest(self.hive_manifest, log_errors=False)
            self.kubectl.delete_manifest(self.postgres_manifest, log_errors=False)
    
    def status(self) -> Dict[str, Any]:
        """Get system status from Kubernetes."""
        status = self.kubectl.get_status()
        self._is_running = status.get("running", False)
        return status
    
    # ========== Port Forwarding ==========
    
    def is_port_forwarding_active(self) -> bool:
        """Check if port forwarding is currently active."""
        return self.port_forwarder.is_active()
    
    def is_minio_port_forwarding_active(self) -> bool:
        """Check if MinIO port forwarding is currently active."""
        return self.minio_port_forwarder.is_active()
    
    def ensure_port_forwarding(self) -> bool:
        """Ensure port forwarding is active."""
        if self.port_forwarder.is_active():
            logger.info(f"Port forwarding already active on port {self.local_port}")
            return True
        
        # Check if Trino is running
        status = self.status()
        if not status.get("running"):
            logger.warning("Trino is not running in Kubernetes. Start it first.")
            return False
        
        logger.info("Port forwarding not active, starting...")
        self.start_port_forwarding()
        return self.port_forwarder.is_active()
    
    def start_port_forwarding(self, include_minio: bool = False) -> None:
        """Start kubectl port-forward for Trino and optionally MinIO."""
        self.port_forwarder.start()
        
        if include_minio:
            logger.info("Starting MinIO port forwarding...")
            self.minio_port_forwarder.start(service_name=Defaults.ServiceNames.MINIO)
            # Also forward console port (9001)
            import subprocess
            import time
            console_cmd = [
                "kubectl", "--context", self.context, "--namespace", self.namespace,
                "port-forward", f"svc/{Defaults.ServiceNames.MINIO}", 
                f"{Defaults.MinIO.CONSOLE_PORT}:{Defaults.MinIO.CONSOLE_PORT}"
            ]
            console_log = open(Path("log/port-forward-minio-console.log"), "w")
            subprocess.Popen(
                console_cmd,
                stdout=console_log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True
            )
            time.sleep(1)  # Give it time to start
    
    def stop_port_forwarding(self, include_minio: bool = True) -> None:
        """Stop the port forwarding process(es)."""
        self.port_forwarder.stop()
        
        if include_minio:
            self.minio_port_forwarder.stop()
            # Also stop console port forward
            import subprocess
            try:
                cmd = ["lsof", "-t", "-i", f":{Defaults.MinIO.CONSOLE_PORT}"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            subprocess.run(["kill", pid], check=False)
            except Exception as e:
                logger.debug(f"Failed to stop console port forward: {e}")
