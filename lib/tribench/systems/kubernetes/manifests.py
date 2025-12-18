"""
Kubernetes manifest generation.

Generates Kubernetes YAML manifests from system configurations.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from tribench.systems.trino import TrinoSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.utils.config import ConfigurationTemplate, get_config_value
from tribench.defaults import Defaults

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """Generates Kubernetes manifests for various systems."""
    
    def __init__(self, config_tree: Dict[str, Any], context: str, namespace: str):
        """
        Initialize manifest generator.
        
        Args:
            config_tree: Full configuration tree
            context: Kubernetes context
            namespace: Kubernetes namespace
        """
        self.config_tree = config_tree
        self.context = context
        self.namespace = namespace
        self.template = ConfigurationTemplate()
    
    def generate_trino(self, output_path: Path) -> None:
        """
        Generate Trino manifest from TrinoSystem configuration.
        
        Args:
            output_path: Path to write the manifest
        """
        logger.info(f"Generating Trino manifest at {output_path}")
        
        # Calculate worker count
        workers_val = get_config_value(self.config_tree, "tribench.systems.trino.workers", 0)
        if isinstance(workers_val, list):
            worker_count = len(workers_val)
        else:
            worker_count = int(workers_val)
        
        # Auto-detect K8s worker nodes if config is 0
        if worker_count == 0:
            worker_count = self._detect_k8s_workers()
        
        # Determine if coordinator should schedule work
        include_coordinator = worker_count == 0
        
        # Generate coordinator configs
        trino_sys = TrinoSystem(config=self.config_tree)
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
        
        # Generate worker configs
        worker_config = self.config_tree.copy()
        worker_config.put("tribench.systems.trino.coordinator.enabled", False)
        worker_config.put("tribench.systems.trino.coordinator.host", Defaults.ServiceNames.TRINO)
        
        trino_worker_sys = TrinoSystem(config=worker_config)
        trino_worker_sys._create_directories()
        trino_worker_sys._generate_configs()
        
        worker_config_props = (trino_worker_sys.install_path / "etc" / "config.properties").read_text()
        worker_jvm_config = (trino_worker_sys.install_path / "etc" / "jvm.config").read_text()
        worker_node_props = (trino_worker_sys.install_path / "etc" / "node.properties").read_text()
        
        # Remove node.id from worker_node_props to allow K8s/Trino to handle unique IDs for replicas
        worker_node_props = "\n".join([line for line in worker_node_props.splitlines() if not line.strip().startswith("node.id=")])
        
        # Build ConfigMap data
        config_map_data = self._build_config_map(config_props, jvm_config, node_props)
        worker_config_map_data = self._build_config_map(worker_config_props, worker_jvm_config, worker_node_props)
        catalog_map_data = self._build_catalog_map(catalogs)
        
        self.template.generate(
            template_name="k8s-trino.yaml.j2",
            config=self.config_tree,
            output_path=output_path,
            config_map_data=config_map_data,
            worker_config_map_data=worker_config_map_data,
            catalog_map_data=catalog_map_data,
            worker_count=worker_count,
            include_coordinator=include_coordinator
        )
    
    def generate_minio(self, output_path: Path) -> None:
        """
        Generate MinIO manifest.
        
        Args:
            output_path: Path to write the manifest
        """
        logger.info(f"Generating MinIO manifest at {output_path}")
        self.template.generate(
            template_name="k8s-minio.yaml.j2",
            config=self.config_tree,
            output_path=output_path
        )
    
    def generate_postgres(self, output_path: Path) -> None:
        """
        Generate PostgreSQL manifest.
        
        Args:
            output_path: Path to write the manifest
        """
        logger.info(f"Generating PostgreSQL manifest at {output_path}")
        self.template.generate(
            template_name="k8s-postgres.yaml.j2",
            config=self.config_tree,
            output_path=output_path
        )
    
    def generate_hive_metastore(self, output_path: Path) -> None:
        """
        Generate Hive Metastore manifest.
        
        Args:
            output_path: Path to write the manifest
        """
        logger.info(f"Generating Hive Metastore manifest at {output_path}")
        
        hive_sys = HiveMetastoreSystem(config=self.config_tree if self.config_tree else {})
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
            output_path=output_path,
            hive_site=hive_site,
            core_site=core_site
        )
    
    def _detect_k8s_workers(self) -> int:
        """Auto-detect Kubernetes worker node count."""
        try:
            cmd = ["kubectl", "--context", self.context, "get", "nodes", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            nodes = json.loads(result.stdout)
            
            # Count nodes that are NOT control-plane
            k8s_workers = 0
            for node in nodes.get("items", []):
                labels = node["metadata"].get("labels", {})
                if "node-role.kubernetes.io/control-plane" not in labels:
                    k8s_workers += 1
            
            if k8s_workers > 0:
                logger.info(f"Auto-detected {k8s_workers} Kubernetes worker nodes.")
                return k8s_workers
        except Exception as e:
            logger.warning(f"Failed to auto-detect K8s nodes: {e}")
        
        return 0
    
    @staticmethod
    def _build_config_map(config_props: str, jvm_config: str, node_props: str) -> str:
        """Build ConfigMap data for Trino configs."""
        return f"""
  config.properties: |
{ManifestGenerator._indent(config_props, 4)}
  jvm.config: |
{ManifestGenerator._indent(jvm_config, 4)}
  node.properties: |
{ManifestGenerator._indent(node_props, 4)}
"""
    
    @staticmethod
    def _build_catalog_map(catalogs: Dict[str, str]) -> str:
        """Build ConfigMap data for Trino catalogs."""
        catalog_map_data = ""
        for name, content in catalogs.items():
            catalog_map_data += f"""
  {name}: |
{ManifestGenerator._indent(content, 4)}
"""
        return catalog_map_data
    
    @staticmethod
    def _indent(text: str, spaces: int) -> str:
        """Helper to indent text for YAML embedding."""
        return "\n".join(" " * spaces + line for line in text.splitlines())
