"""
Trino system implementation.

Manages Trino lifecycle using Docker, including setup, start, stop, and teardown.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from pyhocon import ConfigTree

from tribench.core.system import System
from tribench.utils.config import ConfigurationLoader, get_config_value
from tribench.defaults import Defaults

from .setup import TrinoSetup
from .config_generator import TrinoConfigGenerator
from .lifecycle import TrinoLifecycle
from .health import TrinoHealthMonitor

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
        
        # Paths (exposed as instance attributes for external access)
        root_path = Path(get_config_value(config, "tribench.app.path.home", "."))
        self.downloads_path = root_path / "downloads"
        self.systems_path = root_path / "systems"
        self.install_path = self.systems_path / f"trino-{self.version}"
        self.logs_path = root_path / "log" / "trino"
        
        # Docker configuration (exposed as instance attributes)
        self.container_name = f"tribench-trino-{self.version}"
        self.network_name = Defaults.ServiceNames.NETWORK
        
        # Initialize components
        self.setup_manager = TrinoSetup(self.version, self.downloads_path, self.install_path, self.logs_path)
        self.config_generator = TrinoConfigGenerator(config, self.install_path, self.network_name)
        self.lifecycle_manager = TrinoLifecycle(self.container_name, self.install_path)
        self.health_monitor = TrinoHealthMonitor(config, self.container_name, self.version, self.name)
        
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
            self.setup_manager.create_directories()
            
            # Download Trino binary (if not cached)
            if not self.setup_manager.is_downloaded():
                logger.info(f"Downloading Trino {self.version}...")
                if not self.setup_manager.download_trino():
                    return False
            else:
                logger.info(f"Trino {self.version} already downloaded")
            
            # Generate configuration files
            logger.info("Generating Trino configuration files...")
            self.config_generator.generate_all_configs()
            
            # Create Docker network if it doesn't exist
            network_name = Defaults.ServiceNames.NETWORK
            self.setup_manager.create_docker_network(network_name)
            
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
        return self.lifecycle_manager.start(
            wait_for_health_callback=self.health_monitor.wait_for_health,
            timeout=Defaults.Timeouts.TRINO
        )
    
    def stop(self, force: bool = False, **kwargs) -> bool:
        """
        Stop Trino system.
        
        Args:
            force: If True, force stop (kill). If False, graceful shutdown.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        return self.lifecycle_manager.stop(force=force)
    
    def teardown(self, keep_data: bool = False, **kwargs) -> bool:
        """
        Tear down Trino system.
        
        Args:
            keep_data: If True, keep data directories. If False, remove everything.
        
        Returns:
            True if teardown successful, False otherwise
        """
        return self.lifecycle_manager.teardown(keep_data=keep_data)
    
    def status(self) -> Dict[str, Any]:
        """
        Get Trino system status.
        
        Returns:
            Dictionary with status information
        """
        return self.health_monitor.get_status(self.lifecycle_manager.is_running)
    
    def is_running(self) -> bool:
        """
        Check if Trino is running.
        
        Returns:
            True if running, False otherwise
        """
        return self.lifecycle_manager.is_running()
    
    def get_logs(self, tail: int = 100, follow: bool = False) -> Optional[str]:
        """
        Get Trino logs.
        
        Args:
            tail: Number of lines to tail
            follow: If True, follow logs (stream)
        
        Returns:
            Log output as string, or None if failed
        """
        return self.lifecycle_manager.get_logs(tail=tail, follow=follow)
    
    def _create_directories(self):
        """Create necessary directories for Trino.
        
        This method is provided for backwards compatibility with code that
        calls it directly (e.g., Kubernetes manifests).
        """
        self.setup_manager.create_directories()
    
    def _generate_configs(self):
        """Generate Trino configuration files from templates.
        
        This method is provided for backwards compatibility with code that
        calls it directly (e.g., Kubernetes manifests).
        """
        self.config_generator.generate_all_configs()
