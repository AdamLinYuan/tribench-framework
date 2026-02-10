"""MinIO system implementation for Iceberg object storage."""

import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

from ..core.system import System
from ..defaults import Defaults

logger = logging.getLogger(__name__)


class MinIOSystem(System):
    """
    MinIO object storage system for Iceberg tables.
    
    Manages MinIO lifecycle using Docker Compose:
    - Automated setup and configuration
    - Health checking via HTTP API
    - Bucket creation
    - Docker-based deployment
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize MinIO system.
        
        Args:
            config: ConfigTree with MinIO configuration. If None, loads from ConfigurationLoader.
        """
        # Load config if not provided
        if config is None:
            from tribench.utils.config import ConfigurationLoader
            loader = ConfigurationLoader()
            config = loader.load()
        
        # Extract version from config
        version = config.get("tribench.systems.minio.version", "latest")
        
        # Initialize parent with name and config
        super().__init__(name="minio", config=config)
        
        self.version = version
        self.host = config.get("tribench.systems.minio.host", Defaults.MinIO.HOST)
        self.port = config.get("tribench.systems.minio.port", Defaults.MinIO.PORT)
        self.console_port = config.get("tribench.systems.minio.console_port", Defaults.MinIO.CONSOLE_PORT)
        self.access_key = config.get("tribench.systems.minio.access_key", Defaults.MinIO.ACCESS_KEY)
        self.secret_key = config.get("tribench.systems.minio.secret_key", Defaults.MinIO.SECRET_KEY)
        self.region = config.get("tribench.systems.minio.region", "us-east-1")
        self.buckets = config.get("tribench.systems.minio.buckets", ["warehouse", "datasets"])
        
        # Docker configuration
        docker_config = config.get("tribench.systems.minio.docker", {})
        self.docker_image = docker_config.get("image", "minio/minio")
        
        # Paths
        systems_path = Path(config.get("tribench.app.path.systems"))
        self.system_dir = systems_path / "minio"
        self.data_dir = self.system_dir / "data"
        self.config_dir = self.system_dir / "config"
        self.compose_file = self.system_dir / "docker-compose.yml"
        
        # Initialize template engine
        from tribench.utils.config import ConfigurationTemplate
        self.template = ConfigurationTemplate()
        
        logger.debug(f"MinIOSystem initialized: {self.name}")
    
    def setup(self) -> None:
        """
        Set up MinIO system.
        
        Creates:
        - Directory structure
        - Docker Compose configuration
        """
        logger.info("Setting up MinIO")
        
        try:
            # Create directories
            self.system_dir.mkdir(parents=True, exist_ok=True)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate Docker Compose file
            self._generate_docker_compose()
            
            # Create Docker network if it doesn't exist
            self._create_docker_network()
            
            logger.info(f"MinIO setup complete: {self.system_dir}")
            
        except Exception as e:
            logger.error(f"MinIO setup failed: {e}")
            raise
    
    def start(self, timeout: int = Defaults.Timeouts.MINIO) -> None:
        """
        Start MinIO container.
        
        Args:
            timeout: Maximum time to wait for startup (seconds)
        """
        logger.info("Starting MinIO...")
        
        try:
            # Start container
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "up", "-d"],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Wait for health
            self._wait_for_health(timeout=timeout)
            
            # Create buckets
            self._create_buckets()
            
            logger.info("MinIO started successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start MinIO: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"MinIO startup failed: {e}")
            raise
    
    def stop(self, force: bool = False) -> None:
        """
        Stop MinIO container.
        
        Args:
            force: If True, force stop (kill) instead of graceful shutdown
        """
        logger.info("Stopping MinIO...")
        
        try:
            if force:
                subprocess.run(
                    ["docker-compose", "-f", str(self.compose_file), "kill"],
                    check=True
                )
            else:
                subprocess.run(
                    ["docker-compose", "-f", str(self.compose_file), "down"],
                    check=True
                )
            
            logger.info("MinIO stopped successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop MinIO: {e}")
            raise
    
    def status(self) -> Dict[str, Any]:
        """
        Get MinIO status.
        
        Returns:
            Dictionary with status information
        """
        try:
            # Check if container is running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=tribench-minio", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            is_running = bool(result.stdout.strip())
            
            status = {
                "running": is_running,
                "host": self.host,
                "api_port": self.port,
                "console_port": self.console_port,
                "access_key": self.access_key,
                "buckets": self.buckets
            }
            
            if is_running:
                health = self._check_health()
                status["health"] = "healthy" if health else "unhealthy"
                
                # List actual buckets
                try:
                    buckets = self._list_buckets()
                    status["existing_buckets"] = buckets
                except Exception:
                    status["existing_buckets"] = []
            else:
                status["health"] = "not_running"
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get MinIO status: {e}")
            return {
                "running": False,
                "health": "error",
                "error": str(e)
            }
    
    def teardown(self, keep_data: bool = False) -> None:
        """
        Tear down MinIO system.
        
        Args:
            keep_data: If True, preserve data directory
        """
        logger.info("Tearing down MinIO...")
        
        try:
            # Stop and remove containers
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "down", "-v"],
                check=True
            )
            
            # Remove system directory if not keeping data
            if not keep_data and self.system_dir.exists():
                import shutil
                shutil.rmtree(self.system_dir)
                logger.info(f"Removed MinIO directory: {self.system_dir}")
            
            logger.info("MinIO teardown complete")
            
        except Exception as e:
            logger.error(f"MinIO teardown failed: {e}")
            raise
    
    def get_logs(self, tail: int = 100, follow: bool = False) -> str:
        """
        Get MinIO container logs.
        
        Args:
            tail: Number of lines to show from end
            follow: If True, follow log output
            
        Returns:
            Log output as string
        """
        try:
            cmd = ["docker-compose", "-f", str(self.compose_file), "logs", f"--tail={tail}"]
            if follow:
                cmd.append("-f")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Combine stdout and stderr
            return result.stdout + result.stderr
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get MinIO logs: {e}")
            return f"Error retrieving logs: {e}"
    
    def _generate_docker_compose(self) -> None:
        """Generate Docker Compose configuration."""
        self.template.generate(
            template_name="minio-compose.yml.j2",
            config=self.config,
            output_path=self.compose_file
        )
        
        logger.debug(f"Generated Docker Compose: {self.compose_file}")
    
    def _create_docker_network(self) -> None:
        """Create Docker network if it doesn't exist."""
        try:
            subprocess.run(
                ["docker", "network", "create", Defaults.ServiceNames.NETWORK],
                capture_output=True,
                check=False  # Don't fail if network already exists
            )
        except Exception as e:
            logger.debug(f"Docker network creation (may already exist): {e}")
    
    def _check_health(self) -> bool:
        """
        Check if MinIO is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/minio/health/live",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    def _wait_for_health(self, timeout: int = Defaults.Timeouts.MINIO, interval: int = 2) -> None:
        """
        Wait for MinIO to become healthy.
        
        Args:
            timeout: Maximum time to wait (seconds)
            interval: Time between health checks (seconds)
        """
        logger.info("Waiting for MinIO to become ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_health():
                logger.info("MinIO is ready")
                return
            
            time.sleep(interval)
            logger.debug(f"Waiting for MinIO... ({int(time.time() - start_time)}s)")
        
        raise TimeoutError(f"MinIO did not become ready within {timeout} seconds")
    
    def _create_buckets(self) -> None:
        """Create configured buckets in MinIO."""
        logger.info(f"Creating buckets: {self.buckets}")
        
        # First, configure the mc alias (required after fresh container start)
        try:
            alias_result = subprocess.run(
                [
                    "docker", "exec", Defaults.ServiceNames.MINIO,
                    "mc", "alias", "set", "local",
                    f"http://localhost:{self.port}",
                    self.access_key,
                    self.secret_key
                ],
                capture_output=True,
                text=True
            )
            
            if alias_result.returncode != 0:
                logger.warning(f"Failed to configure mc alias: {alias_result.stderr}")
                return
            else:
                logger.debug("MinIO client alias 'local' configured successfully")
                
        except Exception as e:
            logger.warning(f"Error configuring mc alias: {e}")
            return
        
        # Now create buckets
        for bucket in self.buckets:
            try:
                # Use mc (MinIO Client) via docker exec
                result = subprocess.run(
                    [
                        "docker", "exec", Defaults.ServiceNames.MINIO,
                        "mc", "mb", f"local/{bucket}", "--ignore-existing"
                    ],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.debug(f"Bucket '{bucket}' created or already exists")
                else:
                    logger.warning(f"Failed to create bucket '{bucket}': {result.stderr}")
                    
            except Exception as e:
                logger.warning(f"Error creating bucket '{bucket}': {e}")
    
    def _list_buckets(self) -> List[str]:
        """
        List all buckets in MinIO.
        
        Returns:
            List of bucket names
        """
        try:
            # Ensure alias is configured
            subprocess.run(
                [
                    "docker", "exec", Defaults.ServiceNames.MINIO,
                    "mc", "alias", "set", "local",
                    f"http://localhost:{self.port}",
                    self.access_key,
                    self.secret_key
                ],
                capture_output=True,
                text=True,
                check=False
            )
            
            result = subprocess.run(
                [
                    "docker", "exec", Defaults.ServiceNames.MINIO,
                    "mc", "ls", "local/"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse bucket names from output
            buckets = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    # Format: [2024-10-30 10:00:00 UTC]   0B bucket-name/
                    parts = line.split()
                    if parts:
                        bucket_name = parts[-1].rstrip('/')
                        buckets.append(bucket_name)
            
            return buckets
            
        except Exception as e:
            logger.warning(f"Failed to list buckets: {e}")
            return []
    
    def create_bucket(self, bucket_name: str) -> bool:
        """
        Create a specific bucket.
        
        Args:
            bucket_name: Name of bucket to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                [
                    "docker", "exec", Defaults.ServiceNames.MINIO,
                    "mc", "mb", f"local/{bucket_name}", "--ignore-existing"
                ],
                capture_output=True,
                text=True
            )
            
            success = result.returncode == 0
            if success:
                logger.info(f"Bucket '{bucket_name}' created successfully")
            else:
                logger.error(f"Failed to create bucket '{bucket_name}': {result.stderr}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating bucket '{bucket_name}': {e}")
            return False
