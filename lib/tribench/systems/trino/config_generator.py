"""
Trino configuration file generation.

Handles generation of Trino config files, JVM settings, catalog configurations,
and Docker Compose files.
"""

import logging
import uuid
from pathlib import Path
from typing import Any
from pyhocon import ConfigTree

from tribench.utils.config import ConfigurationTemplate

logger = logging.getLogger(__name__)


class TrinoConfigGenerator:
    """Generates Trino configuration files from templates."""
    
    def __init__(self, config: ConfigTree, install_path: Path, network_name: str):
        """
        Initialize configuration generator.
        
        Args:
            config: Configuration tree
            install_path: Path to Trino installation
            network_name: Docker network name
        """
        self.config = config
        self.install_path = install_path
        self.network_name = network_name
        self.template = ConfigurationTemplate()
    
    def generate_all_configs(self):
        """Generate all Trino configuration files."""
        self._generate_main_configs()
        self._generate_catalog_configs()
        self._generate_docker_compose()
    
    def _generate_main_configs(self):
        """Generate main Trino configuration files."""
        # Generate config.properties
        config_file = self.install_path / "etc" / "config.properties"
        self.template.generate(
            template_name="trino-config.properties.j2",
            config=self.config,
            output_path=config_file
        )
        logger.debug(f"Generated: {config_file}")
        
        # Generate jvm.config
        jvm_file = self.install_path / "etc" / "jvm.config"
        self.template.generate(
            template_name="trino-jvm.config.j2",
            config=self.config,
            output_path=jvm_file
        )
        logger.debug(f"Generated: {jvm_file}")
        
        # Generate node.properties
        self._generate_node_properties()
    
    def _generate_node_properties(self):
        """Generate node.properties with unique node ID."""
        node_id = str(uuid.uuid4())
        node_file = self.install_path / "etc" / "node.properties"
        
        # Ensure defaults for node properties
        if not self.config.get("tribench.systems.trino.node.environment", None):
            self.config.put("tribench.systems.trino.node.environment", "tribench")
        if not self.config.get("tribench.systems.trino.node.data_dir", None):
            self.config.put("tribench.systems.trino.node.data_dir", "/data/trino")
            
        self.template.generate(
            template_name="trino-node.properties.j2",
            config=self.config,
            output_path=node_file,
            node_id=node_id
        )
        logger.debug(f"Generated: {node_file}")
    
    def _generate_catalog_configs(self):
        """Generate Trino catalog configuration files."""
        catalog_dir = self.install_path / "etc" / "catalog"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Iceberg catalog
        iceberg_file = catalog_dir / "iceberg.properties"
        self.template.generate(
            template_name="trino-catalog-iceberg.properties.j2",
            config=self.config,
            output_path=iceberg_file
        )
        logger.debug(f"Generated: {iceberg_file}")
        
        # Generate Hive catalog (for external table staging)
        hive_file = catalog_dir / "hive.properties"
        self.template.generate(
            template_name="trino-catalog-hive.properties.j2",
            config=self.config,
            output_path=hive_file
        )
        logger.debug(f"Generated: {hive_file}")
        
        # Generate TPCH catalog
        tpch_file = catalog_dir / "tpch.properties"
        with open(tpch_file, "w") as f:
            f.write("connector.name=tpch\n")
        logger.debug(f"Generated: {tpch_file}")

        # Generate Memory catalog
        memory_file = catalog_dir / "memory.properties"
        with open(memory_file, "w") as f:
            f.write("connector.name=memory\n")
            f.write("memory.max-data-per-node=128MB\n")
        logger.debug(f"Generated: {memory_file}")
    
    def _generate_docker_compose(self):
        """Generate Docker Compose configuration."""
        compose_file = self.install_path / "docker-compose.yml"
        
        # Ensure defaults for docker compose
        if not self.config.get("tribench.systems.trino.docker.network", None):
            self.config.put("tribench.systems.trino.docker.network", self.network_name)
            
        self.template.generate(
            template_name="trino-compose.yml.j2",
            config=self.config,
            output_path=compose_file
        )
        logger.debug(f"Generated: {compose_file}")
