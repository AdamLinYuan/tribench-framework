"""
Trino container lifecycle management.

Handles starting, stopping, and tearing down Trino Docker containers.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from tribench.defaults import Defaults

logger = logging.getLogger(__name__)


class TrinoLifecycle:
    """Manages Trino Docker container lifecycle."""
    
    def __init__(self, container_name: str, install_path: Path):
        """
        Initialize lifecycle manager.
        
        Args:
            container_name: Docker container name
            install_path: Path to Trino installation
        """
        self.container_name = container_name
        self.install_path = install_path
    
    def is_running(self) -> bool:
        """
        Check if Trino container is running.
        
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
    
    def start(self, wait_for_health_callback=None, timeout: int = Defaults.Timeouts.TRINO) -> bool:
        """
        Start Trino using Docker Compose.
        
        Args:
            wait_for_health_callback: Optional callback function to wait for health
            timeout: Timeout for health check
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("Starting Trino...")
            
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
            
            logger.info("Trino container started")
            
            # Wait for health if callback provided
            if wait_for_health_callback:
                logger.info("Waiting for health check...")
                if wait_for_health_callback(timeout=timeout):
                    logger.info("Trino started successfully")
                    return True
                else:
                    logger.error("Trino failed to become healthy")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Trino: {e}", exc_info=True)
            return False
    
    def stop(self, force: bool = False) -> bool:
        """
        Stop Trino container.
        
        Args:
            force: If True, force stop (kill). If False, graceful shutdown.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping Trino...")
            
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
            
            logger.info("Trino stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Trino: {e}", exc_info=True)
            return False
    
    def teardown(self, keep_data: bool = False) -> bool:
        """
        Tear down Trino installation.
        
        Args:
            keep_data: If True, keep data directories. If False, remove everything.
        
        Returns:
            True if teardown successful, False otherwise
        """
        try:
            logger.info("Tearing down Trino...")
            
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
            
            logger.info("Trino teardown complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to teardown Trino: {e}", exc_info=True)
            return False
    
    def get_logs(self, tail: int = 100, follow: bool = False) -> Optional[str]:
        """
        Get Trino container logs.
        
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
                # Stream logs - caller should handle streaming
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                return None
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
                # Docker logs go to both stdout and stderr, combine them
                output = result.stdout + result.stderr if result.returncode == 0 else None
                return output if output else None
                
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return None
    
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
