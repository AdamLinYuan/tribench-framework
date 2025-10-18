"""
Trino system implementation for TriBench.

Manages Trino lifecycle using Docker, including setup, start, stop, and teardown.
"""

import os
import time
import logging
import requests
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from pyhocon import ConfigTree

from tribench.core.system import System
from tribench.utils.config import ConfigurationLoader, get_config_value

logger = logging.getLogger(__name__)


class TrinoSystem(System):
    """
    Trino system implementation using Docker.
    
    Manages Trino coordinator lifecycle, including:
    - Binary download and caching
    - Docker Compose generation from configuration
    - Container lifecycle management
    - Health checking and status monitoring
    """
    
    def __init__(self, config: Optional[ConfigTree] = None):
        """
        Initialize Trino system.
        
        Args:
            config: Configuration tree. If None, loads from ConfigurationLoader.
        """
        if config is None:
            loader = ConfigurationLoader()
            config = loader.load()
        
        self.version = get_config_value(config, "tribench.systems.trino.version", "434")
        
        # Initialize parent with name and config
        super().__init__(name=f"trino-{self.version}", config=config)
        
        self.config = config
        self.name = f"trino-{self.version}"
        
        # Paths
        root_path = Path(get_config_value(config, "tribench.app.path.home", "."))
        self.downloads_path = root_path / "downloads"
        self.systems_path = root_path / "systems"
        self.install_path = self.systems_path / f"trino-{self.version}"
        self.logs_path = root_path / "log" / "trino"
        
        # Docker configuration
        self.container_name = f"tribench-trino-{self.version}"
        self.network_name = "tribench-network"
        
        logger.info(f"Initialized Trino system version {self.version}")
    
    def setup(self, **kwargs) -> bool:
        """
        Set up Trino system.
        
        Steps:
        1. Create necessary directories
        2. Download Trino binary (if needed)
        3. Generate configuration files from templates
        4. Generate Docker Compose file
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            logger.info(f"Setting up Trino {self.version}...")
            
            # Create directories
            self._create_directories()
            
            # Download Trino binary (if not cached)
            if not self._is_downloaded():
                logger.info(f"Downloading Trino {self.version}...")
                if not self._download_trino():
                    return False
            else:
                logger.info(f"Trino {self.version} already downloaded")
            
            # Generate configuration files
            logger.info("Generating Trino configuration files...")
            self._generate_configs()
            
            # Generate Docker Compose file
            logger.info("Generating Docker Compose configuration...")
            self._generate_docker_compose()
            
            # Create Docker network if it doesn't exist
            self._create_docker_network()
            
            logger.info(f"Trino {self.version} setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Trino: {e}", exc_info=True)
            return False
    
    def start(self, **kwargs) -> bool:
        """
        Start Trino system using Docker Compose.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info(f"Starting Trino {self.version}...")
            
            # Check if already running
            if self.is_running():
                logger.warning("Trino is already running")
                return True
            
            # Start with docker-compose
            compose_file = self.install_path / "docker-compose.yml"
            if not compose_file.exists():
                logger.error("Docker Compose file not found. Run setup first.")
                return False
            
            cmd = [
                "docker-compose",
                "-f", str(compose_file),
                "up", "-d"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.install_path)
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start Trino: {result.stderr}")
                return False
            
            logger.info("Trino container started, waiting for health check...")
            
            # Wait for Trino to be healthy
            if self._wait_for_health(timeout=120):
                logger.info(f"Trino {self.version} started successfully")
                return True
            else:
                logger.error("Trino failed to become healthy")
                return False
            
        except Exception as e:
            logger.error(f"Failed to start Trino: {e}", exc_info=True)
            return False
    
    def stop(self, force: bool = False, **kwargs) -> bool:
        """
        Stop Trino system.
        
        Args:
            force: If True, force stop (kill). If False, graceful shutdown.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            logger.info(f"Stopping Trino {self.version}...")
            
            if not self.is_running():
                logger.warning("Trino is not running")
                return True
            
            compose_file = self.install_path / "docker-compose.yml"
            if not compose_file.exists():
                logger.warning("Docker Compose file not found, using container name")
                return self._stop_by_container_name(force)
            
            if force:
                cmd = ["docker-compose", "-f", str(compose_file), "kill"]
                logger.info("Force stopping Trino...")
            else:
                cmd = ["docker-compose", "-f", str(compose_file), "down"]
                logger.info("Gracefully stopping Trino...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.install_path)
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to stop Trino: {result.stderr}")
                return False
            
            logger.info(f"Trino {self.version} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Trino: {e}", exc_info=True)
            return False
    
    def teardown(self, keep_data: bool = False, **kwargs) -> bool:
        """
        Tear down Trino system.
        
        Args:
            keep_data: If True, keep data directories. If False, remove everything.
        
        Returns:
            True if teardown successful, False otherwise
        """
        try:
            logger.info(f"Tearing down Trino {self.version}...")
            
            # Stop if running
            if self.is_running():
                logger.info("Stopping running Trino instance...")
                self.stop(force=True)
            
            # Remove Docker containers and volumes
            compose_file = self.install_path / "docker-compose.yml"
            if compose_file.exists():
                cmd = ["docker-compose", "-f", str(compose_file), "down", "-v"]
                subprocess.run(cmd, capture_output=True, cwd=str(self.install_path))
            
            # Remove installation directory
            if not keep_data and self.install_path.exists():
                logger.info(f"Removing installation directory: {self.install_path}")
                import shutil
                shutil.rmtree(self.install_path)
            
            logger.info(f"Trino {self.version} teardown complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to teardown Trino: {e}", exc_info=True)
            return False
    
    def status(self) -> Dict[str, Any]:
        """
        Get Trino system status.
        
        Returns:
            Dictionary with status information
        """
        status = {
            "name": self.name,
            "version": self.version,
            "running": self.is_running(),
            "healthy": False,
            "container_id": None,
            "ports": {},
            "endpoints": {}
        }
        
        try:
            # Check if container is running
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.ID}}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                status["container_id"] = result.stdout.strip()
                status["running"] = True
                
                # Get port mappings
                port_result = subprocess.run(
                    ["docker", "port", status["container_id"]],
                    capture_output=True,
                    text=True
                )
                
                if port_result.returncode == 0:
                    for line in port_result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split(' -> ')
                            if len(parts) == 2:
                                container_port = parts[0].split('/')[0]
                                host_port = parts[1].split(':')[-1]
                                status["ports"][container_port] = host_port
                
                # Check health
                status["healthy"] = self._check_health()
                
                # Set endpoints
                if status["healthy"]:
                    port = get_config_value(self.config, "tribench.systems.trino.coordinator.port", 8080)
                    host = get_config_value(self.config, "tribench.systems.trino.coordinator.host", "localhost")
                    status["endpoints"]["ui"] = f"http://{host}:{port}"
                    status["endpoints"]["api"] = f"http://{host}:{port}/v1/info"
            
        except Exception as e:
            logger.error(f"Failed to get Trino status: {e}")
            status["error"] = str(e)
        
        return status
    
    def is_running(self) -> bool:
        """
        Check if Trino is running.
        
        Returns:
            True if running, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def get_logs(self, tail: int = 100, follow: bool = False) -> Optional[str]:
        """
        Get Trino logs.
        
        Args:
            tail: Number of lines to tail
            follow: If True, follow logs (stream)
        
        Returns:
            Log output as string, or None if failed
        """
        try:
            cmd = ["docker", "logs", f"--tail={tail}"]
            if follow:
                cmd.append("-f")
            cmd.append(self.container_name)
            
            if follow:
                # Stream logs
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                return None  # Caller should handle streaming
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
                # Docker logs go to both stdout and stderr, combine them
                output = result.stdout + result.stderr if result.returncode == 0 else None
                return output if output else None
                
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return None
    
    # Private helper methods
    
    def _create_directories(self):
        """Create necessary directories for Trino."""
        directories = [
            self.downloads_path,
            self.systems_path,
            self.install_path,
            self.install_path / "etc" / "catalog",
            self.logs_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    def _is_downloaded(self) -> bool:
        """Check if Trino binary is already downloaded."""
        tarball = self.downloads_path / f"trino-server-{self.version}.tar.gz"
        return tarball.exists()
    
    def _download_trino(self) -> bool:
        """Download Trino binary."""
        try:
            base_url = "https://repo1.maven.org/maven2/io/trino/trino-server"
            download_url = f"{base_url}/{self.version}/trino-server-{self.version}.tar.gz"
            tarball_path = self.downloads_path / f"trino-server-{self.version}.tar.gz"
            
            logger.info(f"Downloading from: {download_url}")
            
            # Use curl for download (more reliable than requests for large files)
            cmd = ["curl", "-L", "-o", str(tarball_path), download_url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Download failed: {result.stderr}")
                return False
            
            logger.info(f"Downloaded to: {tarball_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download Trino: {e}")
            return False
    
    def _generate_configs(self):
        """Generate Trino configuration files from templates."""
        from tribench.utils.config import ConfigurationTemplate
        
        template_gen = ConfigurationTemplate()
        
        # Generate config.properties
        config_content = self._generate_config_properties()
        config_file = self.install_path / "etc" / "config.properties"
        config_file.write_text(config_content)
        logger.debug(f"Generated: {config_file}")
        
        # Generate jvm.config
        jvm_content = self._generate_jvm_config()
        jvm_file = self.install_path / "etc" / "jvm.config"
        jvm_file.write_text(jvm_content)
        logger.debug(f"Generated: {jvm_file}")
        
        # Generate node.properties
        node_content = self._generate_node_properties()
        node_file = self.install_path / "etc" / "node.properties"
        node_file.write_text(node_content)
        logger.debug(f"Generated: {node_file}")
        
        # Generate catalog configurations
        self._generate_catalog_configs()
    
    def _generate_config_properties(self) -> str:
        """Generate config.properties content."""
        port = get_config_value(self.config, "tribench.systems.trino.coordinator.port", 8080)
        host = get_config_value(self.config, "tribench.systems.trino.coordinator.host", "localhost")
        
        return f"""# Trino Configuration
# Generated by TriBench

coordinator=true
node-scheduler.include-coordinator=true
http-server.http.port={port}
discovery.uri=http://{host}:{port}

query.max-memory=1GB
query.max-memory-per-node=512MB
"""
    
    def _generate_jvm_config(self) -> str:
        """Generate jvm.config content."""
        heap = get_config_value(self.config, "tribench.systems.trino.coordinator.jvm.heap", "2G")
        
        return f"""-server
-Xmx{heap}
-XX:InitialRAMPercentage=80
-XX:MaxRAMPercentage=80
-XX:G1HeapRegionSize=32M
-XX:+ExplicitGCInvokesConcurrent
-XX:+HeapDumpOnOutOfMemoryError
-XX:+ExitOnOutOfMemoryError
-XX:-OmitStackTraceInFastThrow
-XX:ReservedCodeCacheSize=512M
-Djdk.attach.allowAttachSelf=true
-Djdk.nio.maxCachedBufferSize=2000000
"""
    
    def _generate_node_properties(self) -> str:
        """Generate node.properties content."""
        import uuid
        node_id = str(uuid.uuid4())
        
        return f"""# Node Properties
node.environment=tribench
node.id={node_id}
node.data-dir=/data/trino
"""
    
    def _generate_catalog_configs(self):
        """Generate catalog configuration files."""
        catalog_dir = self.install_path / "etc" / "catalog"
        
        # Memory catalog
        memory_catalog = catalog_dir / "memory.properties"
        memory_catalog.write_text("connector.name=memory\n")
        
        # TPC-H catalog
        tpch_catalog = catalog_dir / "tpch.properties"
        tpch_catalog.write_text("connector.name=tpch\ntpch.splits-per-node=4\n")
        
        logger.debug(f"Generated catalog configs in: {catalog_dir}")
    
    def _generate_docker_compose(self):
        """Generate Docker Compose configuration."""
        port = get_config_value(self.config, "tribench.systems.trino.coordinator.port", 8080)
        
        compose_content = f"""version: '3.8'

services:
  trino:
    image: trinodb/trino:{self.version}
    container_name: {self.container_name}
    ports:
      - "{port}:{port}"
    volumes:
      - ./etc:/etc/trino
      - trino-data:/data
    networks:
      - {self.network_name}
    environment:
      - JAVA_TOOL_OPTIONS=-Xmx2G
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:{port}/v1/info || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  trino-data:
    driver: local

networks:
  {self.network_name}:
    external: true
"""
        
        compose_file = self.install_path / "docker-compose.yml"
        compose_file.write_text(compose_content)
        logger.debug(f"Generated: {compose_file}")
    
    def _create_docker_network(self):
        """Create Docker network if it doesn't exist."""
        try:
            # Check if network exists
            result = subprocess.run(
                ["docker", "network", "ls", "--filter", f"name={self.network_name}", "--format", "{{.Name}}"],
                capture_output=True,
                text=True
            )
            
            if self.network_name not in result.stdout:
                logger.info(f"Creating Docker network: {self.network_name}")
                subprocess.run(
                    ["docker", "network", "create", self.network_name],
                    capture_output=True,
                    check=True
                )
        except Exception as e:
            logger.warning(f"Failed to create Docker network: {e}")
    
    def _wait_for_health(self, timeout: int = 120) -> bool:
        """
        Wait for Trino to be healthy.
        
        Args:
            timeout: Timeout in seconds
        
        Returns:
            True if healthy, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._check_health():
                return True
            time.sleep(5)
            logger.debug("Waiting for Trino to be healthy...")
        
        return False
    
    def _check_health(self) -> bool:
        """
        Check if Trino is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            port = get_config_value(self.config, "tribench.systems.trino.coordinator.port", 8080)
            host = get_config_value(self.config, "tribench.systems.trino.coordinator.host", "localhost")
            url = f"http://{host}:{port}/v1/info"
            
            response = requests.get(url, timeout=5)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _stop_by_container_name(self, force: bool = False) -> bool:
        """Stop container by name when compose file not available."""
        try:
            if force:
                cmd = ["docker", "kill", self.container_name]
            else:
                cmd = ["docker", "stop", self.container_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to stop container: {result.stderr}")
                return False
            
            # Remove container
            subprocess.run(["docker", "rm", self.container_name], capture_output=True)
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            return False
