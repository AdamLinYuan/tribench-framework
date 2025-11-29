"""
Hive Metastore System Implementation

Manages Apache Hive Metastore for Iceberg catalog metadata storage.
Hive Metastore uses PostgreSQL as the backend database and MinIO for warehouse storage.
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

import requests

from tribench.core.system import System


logger = logging.getLogger(__name__)


class HiveMetastoreSystem(System):
    """
    Hive Metastore system management.
    
    Hive Metastore stores metadata for Iceberg tables and uses:
    - PostgreSQL as the backend database (metastore DB)
    - MinIO (S3-compatible) for warehouse storage (s3a://)
    
    Attributes:
        version: Hive version to use
        port: Thrift service port (default: 9083)
        warehouse_dir: S3 warehouse directory (default: s3a://warehouse/)
        postgres_host: PostgreSQL host for backend
        postgres_db: PostgreSQL database name
        minio_endpoint: MinIO endpoint for S3 access
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Hive Metastore system.
        
        Args:
            config: Configuration dictionary. If None, loads from ConfigurationLoader.
        """
        # Load config if not provided
        if config is None:
            from tribench.utils.config import ConfigurationLoader
            loader = ConfigurationLoader()
            config = loader.load()
        
        super().__init__(name="hive-metastore", config=config)
        
        # Load Hive-specific configuration
        hive_config = self.config.get('tribench.systems.hive_metastore', {})
        
        self.version = hive_config.get('version', '4.0.0')
        self.port = hive_config.get('port', 9083)
        self.warehouse_dir = hive_config.get('warehouse_dir', 's3a://warehouse/')
        
        # PostgreSQL backend configuration
        postgres_config = self.config.get('tribench.systems.postgresql', {})
        self.postgres_host = postgres_config.get('docker', {}).get('service_name', 'tribench-postgresql')
        postgres_databases = postgres_config.get('databases', {})
        metastore_db = postgres_databases.get('metastore', {})
        self.postgres_db = metastore_db.get('name', 'metastore')
        self.postgres_user = metastore_db.get('user', 'hive')
        self.postgres_password = metastore_db.get('password', 'hivepassword')
        
        # MinIO configuration
        minio_config = self.config.get('tribench.systems.minio', {})
        minio_docker = minio_config.get('docker', {})
        self.minio_host = minio_docker.get('service_name', 'tribench-minio')
        self.minio_port = minio_config.get('api_port', 9000)
        self.minio_access_key = minio_config.get('root_user', 'minioadmin')
        self.minio_secret_key = minio_config.get('root_password', 'minioadmin')
        self.minio_endpoint = f"http://{self.minio_host}:{self.minio_port}"
        
        # Docker configuration
        docker_config = hive_config.get('docker', {})
        self.service_name = docker_config.get('service_name', 'tribench-hive-metastore')
        self.network = docker_config.get('network', 'tribench-network')
        
        # Directories
        framework_root = Path(self.config.get('tribench.paths.framework_root', os.getcwd()))
        systems_dir = framework_root / 'systems'
        
        self.system_dir = systems_dir / f"hive-metastore-{self.version}"
        self.conf_dir = self.system_dir / 'conf'
        
        # Initialize template engine
        from tribench.utils.config import ConfigurationTemplate
        self.template = ConfigurationTemplate()
        
        logger.info(f"Initialized Hive Metastore system (version={self.version}, port={self.port})")
    
    def setup(self) -> None:
        """
        Set up Hive Metastore system.
        
        Creates necessary directories, configuration files, and Docker Compose configuration.
        """
        logger.info("Setting up Hive Metastore...")
        
        # Create directories
        self.system_dir.mkdir(parents=True, exist_ok=True)
        self.conf_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created directories: {self.system_dir}")
        
        # Generate configuration files
        self._generate_metastore_site()
        self._generate_core_site()
        self._generate_dockerfile()
        self._generate_docker_compose()
        
        logger.info("Hive Metastore setup complete")
    
    def start(self, wait_for_health: bool = True, timeout: int = 120) -> None:
        """
        Start Hive Metastore system.
        
        Args:
            wait_for_health: Wait for health check to pass
            timeout: Health check timeout in seconds
        """
        logger.info("Starting Hive Metastore...")
        
        # Ensure Docker network exists
        self._ensure_docker_network()
        
        # Start Docker Compose
        compose_file = self.system_dir / 'docker-compose.yml'
        cmd = ['docker-compose', '-f', str(compose_file), 'up', '-d']
        
        logger.debug(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start Hive Metastore: {result.stderr}")
        
        logger.info(f"Hive Metastore container started")
        
        # Wait for health check
        if wait_for_health:
            logger.info("Waiting for Hive Metastore to become healthy...")
            if not self._wait_for_health(timeout):
                raise RuntimeError("Hive Metastore health check timed out")
            
            logger.info("Hive Metastore is healthy and ready")
    
    def stop(self, force: bool = False) -> None:
        """
        Stop Hive Metastore system.
        
        Args:
            force: Force stop without graceful shutdown
        """
        logger.info("Stopping Hive Metastore...")
        
        compose_file = self.system_dir / 'docker-compose.yml'
        
        if not compose_file.exists():
            logger.warning("Docker Compose file not found, nothing to stop")
            return
        
        cmd = ['docker-compose', '-f', str(compose_file), 'down']
        if force:
            cmd.append('--timeout')
            cmd.append('0')
        
        logger.debug(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Failed to stop Hive Metastore: {result.stderr}")
        else:
            logger.info("Hive Metastore stopped")
    
    def status(self) -> Dict[str, any]:
        """
        Get Hive Metastore system status.
        
        Returns:
            Status dictionary with keys:
                - running: Whether container is running
                - healthy: Whether health check passes
                - port: Thrift service port
                - warehouse: Warehouse directory
        """
        status = {
            'running': False,
            'healthy': False,
            'port': self.port,
            'warehouse': self.warehouse_dir,
        }
        
        # Check if container is running
        cmd = ['docker', 'ps', '--filter', f'name={self.service_name}', '--format', '{{.Names}}']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and self.service_name in result.stdout:
            status['running'] = True
            status['healthy'] = self._check_health()
        
        return status
    
    def teardown(self, keep_data: bool = False) -> None:
        """
        Tear down Hive Metastore system.
        
        Args:
            keep_data: If True, keep configuration and data directories
        """
        logger.info("Tearing down Hive Metastore...")
        
        # Stop containers
        self.stop(force=True)
        
        # Remove Docker resources
        compose_file = self.system_dir / 'docker-compose.yml'
        if compose_file.exists():
            cmd = ['docker-compose', '-f', str(compose_file), 'down', '-v']
            subprocess.run(cmd, capture_output=True, text=True)
        
        # Remove directories
        if not keep_data:
            import shutil
            if self.system_dir.exists():
                shutil.rmtree(self.system_dir)
                logger.info(f"Removed system directory: {self.system_dir}")
        else:
            logger.info(f"Kept data in: {self.system_dir}")
        
        logger.info("Hive Metastore teardown complete")
    
    def get_logs(self, tail: int = 100, follow: bool = False) -> str:
        """
        Get Hive Metastore logs.
        
        Args:
            tail: Number of lines to show from end
            follow: Follow log output (stream mode)
            
        Returns:
            Log output as string
        """
        cmd = ['docker', 'logs', self.service_name, '--tail', str(tail)]
        
        if follow:
            cmd.append('--follow')
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get logs: {result.stderr}")
        
        return result.stdout
    
    def _check_health(self) -> bool:
        """
        Check if Hive Metastore is healthy.
        
        Checks if the Thrift service port is accepting connections.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if Thrift port is open using netcat in container
            cmd = [
                'docker', 'exec', self.service_name,
                'nc', '-z', 'localhost', str(self.port)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    def _wait_for_health(self, timeout: int = 120) -> bool:
        """
        Wait for Hive Metastore to become healthy.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if healthy within timeout, False otherwise
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._check_health():
                return True
            
            logger.debug("Waiting for Hive Metastore to be ready...")
            time.sleep(5)
        
        return False
    
    def _generate_metastore_site(self) -> None:
        """Generate hive-site.xml configuration for metastore."""
        config_file = self.conf_dir / 'hive-site.xml'
        
        self.template.generate(
            template_name="hive-site.xml.j2",
            config=self.config,
            output_path=config_file
        )
        
        logger.info(f"Generated hive-site.xml: {config_file}")
    
    def _generate_core_site(self) -> None:
        """Generate core-site.xml for Hadoop configuration."""
        config_file = self.conf_dir / 'core-site.xml'
        
        self.template.generate(
            template_name="core-site.xml.j2",
            config=self.config,
            output_path=config_file
        )
        
        logger.info(f"Generated core-site.xml: {config_file}")
    
    def _generate_dockerfile(self) -> None:
        """Generate Dockerfile that adds PostgreSQL JDBC driver and Hadoop AWS libraries to Hive image."""
        dockerfile_path = self.system_dir / 'Dockerfile'
        
        self.template.generate(
            template_name="hive-dockerfile.j2",
            config=self.config,
            output_path=dockerfile_path
        )
        
        logger.info(f"Generated Dockerfile: {dockerfile_path}")

    
    def _generate_docker_compose(self) -> None:
        """Generate Docker Compose configuration."""
        compose_file = self.system_dir / 'docker-compose.yml'
        
        self.template.generate(
            template_name="hive-compose.yml.j2",
            config=self.config,
            output_path=compose_file
        )
        
        logger.info(f"Generated Docker Compose config: {compose_file}")
    
    def _ensure_docker_network(self) -> None:
        """Ensure Docker network exists."""
        cmd = ['docker', 'network', 'inspect', self.network]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Network doesn't exist, create it
            cmd = ['docker', 'network', 'create', self.network]
            subprocess.run(cmd, check=True)
            logger.info(f"Created Docker network: {self.network}")
