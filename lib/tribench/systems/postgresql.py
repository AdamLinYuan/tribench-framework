"""PostgreSQL system implementation for Hive Metastore backend."""

import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from ..core.system import System

logger = logging.getLogger(__name__)


class PostgreSQLSystem(System):
    """
    PostgreSQL database system for Hive Metastore backend.
    
    Manages PostgreSQL lifecycle using Docker Compose:
    - Automated setup and configuration
    - Health checking via pg_isready
    - Database and user creation
    - Docker-based deployment
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize PostgreSQL system.
        
        Args:
            config: ConfigTree with PostgreSQL configuration. If None, loads from ConfigurationLoader.
        """
        # Load config if not provided
        if config is None:
            from tribench.utils.config import ConfigurationLoader
            loader = ConfigurationLoader()
            config = loader.load()
        
        # Extract version from config
        version = config.get("tribench.systems.postgresql.version", "15")
        
        # Initialize parent with name and config
        super().__init__(name="postgresql", config=config)
        
        self.version = version
        self.host = config.get("tribench.systems.postgresql.host", "localhost")
        self.port = config.get("tribench.systems.postgresql.port", 5432)
        self.databases = config.get("tribench.systems.postgresql.databases", {})
        
        # Docker configuration
        docker_config = config.get("tribench.systems.postgresql.docker", {})
        self.docker_image = docker_config.get("image", "postgres")
        self.docker_tag = str(version)
        
        # Paths
        systems_path = Path(config.get("tribench.app.path.systems"))
        self.system_dir = systems_path / f"postgresql-{version}"
        self.data_dir = self.system_dir / "data"
        self.init_dir = self.system_dir / "init"
        self.compose_file = self.system_dir / "docker-compose.yml"
        
        # Initialize template engine
        from tribench.utils.config import ConfigurationTemplate
        self.template = ConfigurationTemplate()
        
        logger.debug(f"PostgreSQLSystem initialized: {self.name} version {self.version}")
    
    def setup(self) -> None:
        """
        Set up PostgreSQL system.
        
        Creates:
        - Directory structure
        - Initialization scripts for databases
        - Docker Compose configuration
        """
        logger.info(f"Setting up PostgreSQL version {self.version}")
        
        try:
            # Create directories
            self.system_dir.mkdir(parents=True, exist_ok=True)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.init_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate initialization scripts
            self._generate_init_scripts()
            
            # Generate Docker Compose file
            self._generate_docker_compose()
            
            # Create Docker network if it doesn't exist
            self._create_docker_network()
            
            logger.info(f"PostgreSQL setup complete: {self.system_dir}")
            
        except Exception as e:
            logger.error(f"PostgreSQL setup failed: {e}")
            raise
    
    def start(self, timeout: int = 60) -> None:
        """
        Start PostgreSQL container.
        
        Args:
            timeout: Maximum time to wait for startup (seconds)
        """
        logger.info("Starting PostgreSQL...")
        
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
            
            # Initialize databases
            self._initialize_databases()
            
            logger.info("PostgreSQL started successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start PostgreSQL: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"PostgreSQL startup failed: {e}")
            raise
    
    def stop(self, force: bool = False) -> None:
        """
        Stop PostgreSQL container.
        
        Args:
            force: If True, force stop (kill) instead of graceful shutdown
        """
        logger.info("Stopping PostgreSQL...")
        
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
            
            logger.info("PostgreSQL stopped successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop PostgreSQL: {e}")
            raise
    
    def status(self) -> Dict[str, Any]:
        """
        Get PostgreSQL status.
        
        Returns:
            Dictionary with status information
        """
        try:
            # Check if container is running
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name=tribench-postgresql-{self.version}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            is_running = bool(result.stdout.strip())
            
            status = {
                "running": is_running,
                "version": self.version,
                "host": self.host,
                "port": self.port,
                "databases": list(self.databases.keys())
            }
            
            if is_running:
                health = self._check_health()
                status["health"] = "healthy" if health else "unhealthy"
            else:
                status["health"] = "not_running"
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL status: {e}")
            return {
                "running": False,
                "health": "error",
                "error": str(e)
            }
    
    def teardown(self, keep_data: bool = False) -> None:
        """
        Tear down PostgreSQL system.
        
        Args:
            keep_data: If True, preserve data directory
        """
        logger.info("Tearing down PostgreSQL...")
        
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
                logger.info(f"Removed PostgreSQL directory: {self.system_dir}")
            
            logger.info("PostgreSQL teardown complete")
            
        except Exception as e:
            logger.error(f"PostgreSQL teardown failed: {e}")
            raise
    
    def get_logs(self, tail: int = 100, follow: bool = False) -> str:
        """
        Get PostgreSQL container logs.
        
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
            logger.error(f"Failed to get PostgreSQL logs: {e}")
            return f"Error retrieving logs: {e}"
    
    def _generate_init_scripts(self) -> None:
        """Generate initialization SQL scripts for databases."""
        # Create init script for databases
        init_script = self.init_dir / "01-init-databases.sql"
        
        self.template.generate(
            template_name="postgresql-init.sql.j2",
            config=self.config,
            output_path=init_script
        )
        
        logger.debug(f"Generated init script: {init_script}")
    
    def _generate_docker_compose(self) -> None:
        """Generate Docker Compose configuration."""
        self.template.generate(
            template_name="postgresql-compose.yml.j2",
            config=self.config,
            output_path=self.compose_file
        )
        
        logger.debug(f"Generated Docker Compose: {self.compose_file}")
    
    def _create_docker_network(self) -> None:
        """Create Docker network if it doesn't exist."""
        try:
            subprocess.run(
                ["docker", "network", "create", "tribench-network"],
                capture_output=True,
                check=False  # Don't fail if network already exists
            )
        except Exception as e:
            logger.debug(f"Docker network creation (may already exist): {e}")
    
    def _check_health(self) -> bool:
        """
        Check if PostgreSQL is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Use pg_isready via docker exec
            result = subprocess.run(
                [
                    "docker", "exec",
                    f"tribench-postgresql-{self.version}",
                    "pg_isready", "-U", list(self.databases.values())[0].get("user", "postgres")
                ],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    def _wait_for_health(self, timeout: int = 60, interval: int = 2) -> None:
        """
        Wait for PostgreSQL to become healthy.
        
        Args:
            timeout: Maximum time to wait (seconds)
            interval: Time between health checks (seconds)
        """
        logger.info("Waiting for PostgreSQL to become ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_health():
                logger.info("PostgreSQL is ready")
                return
            
            time.sleep(interval)
            logger.debug(f"Waiting for PostgreSQL... ({int(time.time() - start_time)}s)")
        
        raise TimeoutError(f"PostgreSQL did not become ready within {timeout} seconds")
    
    def _initialize_databases(self) -> None:
        """
        Initialize databases after container is running.
        
        The init scripts in docker-entrypoint-initdb.d are only run
        on first container start. This method ensures databases exist.
        """
        logger.info("Verifying databases are initialized...")
        
        # The initialization scripts mounted at /docker-entrypoint-initdb.d
        # will be automatically executed by PostgreSQL on first start
        # We just need to verify they completed successfully
        
        for db_name in self.databases.keys():
            try:
                # Check if database exists
                result = subprocess.run(
                    [
                        "docker", "exec",
                        f"tribench-postgresql-{self.version}",
                        "psql", "-U", list(self.databases.values())[0].get("user", "postgres"),
                        "-lqt"
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if db_name in result.stdout:
                    logger.debug(f"Database '{db_name}' verified")
                else:
                    logger.warning(f"Database '{db_name}' not found in list")
                    
            except Exception as e:
                logger.warning(f"Could not verify database '{db_name}': {e}")
        
        logger.info("Database initialization complete")
