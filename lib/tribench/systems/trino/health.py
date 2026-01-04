"""
Trino health checking and status monitoring.

Handles health checks, status retrieval, and readiness verification.
"""

import logging
import time
import subprocess
import requests
from typing import Dict, Any
from pyhocon import ConfigTree

from tribench.utils.config import get_config_value
from tribench.defaults import Defaults

logger = logging.getLogger(__name__)


class TrinoHealthMonitor:
    """Monitors Trino health and status."""
    
    def __init__(self, config: ConfigTree, container_name: str, version: str, name: str):
        """
        Initialize health monitor.
        
        Args:
            config: Configuration tree
            container_name: Docker container name
            version: Trino version
            name: System name
        """
        self.config = config
        self.container_name = container_name
        self.version = version
        self.name = name
        
        # Get connection details from config
        self.host = get_config_value(config, "tribench.systems.trino.coordinator.host", Defaults.Trino.HOST)
        self.port = get_config_value(config, "tribench.systems.trino.coordinator.port", Defaults.Trino.PORT)
    
    def check_health(self) -> bool:
        """
        Check if Trino is healthy and ready to accept queries.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Step 1: Check if HTTP endpoint is responding
            info_url = f"http://{self.host}:{self.port}/v1/info"
            response = requests.get(info_url, timeout=5)
            if response.status_code != 200:
                return False
            
            # Step 2: Check server state from info endpoint
            info = response.json()
            if info.get('starting', True):  # If 'starting' field exists and is True
                logger.debug("Trino is still starting up...")
                return False

            return True
            
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    def wait_for_health(self, timeout: int = Defaults.Timeouts.TRINO) -> bool:
        """
        Wait for Trino to be healthy.
        
        Args:
            timeout: Timeout in seconds
        
        Returns:
            True if healthy, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.check_health():
                return True
            time.sleep(Defaults.Retry.HEALTH_CHECK_INTERVAL)
            logger.debug("Waiting for Trino to be healthy...")
        
        return False
    
    def get_status(self, is_running_callback) -> Dict[str, Any]:
        """
        Get comprehensive Trino status.
        
        Args:
            is_running_callback: Callback to check if container is running
        
        Returns:
            Dictionary with status information
        """
        status = {
            "name": self.name,
            "version": self.version,
            "running": is_running_callback(),
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
                status["healthy"] = self.check_health()
                
                # Set endpoints
                if status["healthy"]:
                    status["endpoints"]["ui"] = f"http://{self.host}:{self.port}"
                    status["endpoints"]["api"] = f"http://{self.host}:{self.port}/v1/info"
            
        except Exception as e:
            logger.error(f"Failed to get Trino status: {e}")
            status["error"] = str(e)
        
        return status
