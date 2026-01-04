"""
Trino setup and binary management.

Handles downloading Trino binaries and creating directory structures.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TrinoSetup:
    """Manages Trino binary downloads and directory setup."""
    
    def __init__(self, version: str, downloads_path: Path, install_path: Path, logs_path: Path):
        """
        Initialize setup manager.
        
        Args:
            version: Trino version
            downloads_path: Path for downloaded binaries
            install_path: Path for Trino installation
            logs_path: Path for logs
        """
        self.version = version
        self.downloads_path = downloads_path
        self.install_path = install_path
        self.logs_path = logs_path
    
    def create_directories(self):
        """Create necessary directories for Trino."""
        directories = [
            self.downloads_path,
            self.install_path,
            self.install_path / "etc" / "catalog",
            self.logs_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    def is_downloaded(self) -> bool:
        """
        Check if Trino binary is already downloaded.
        
        Returns:
            True if tarball exists, False otherwise
        """
        tarball = self.downloads_path / f"trino-server-{self.version}.tar.gz"
        return tarball.exists()
    
    def download_trino(self) -> bool:
        """
        Download Trino binary from Maven repository.
        
        Returns:
            True if download successful, False otherwise
        """
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
    
    def create_docker_network(self, network_name: str):
        """
        Create Docker network if it doesn't exist.
        
        Args:
            network_name: Name of Docker network to create
        """
        try:
            # Check if network exists
            result = subprocess.run(
                ["docker", "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"],
                capture_output=True,
                text=True
            )
            
            if network_name not in result.stdout:
                logger.info(f"Creating Docker network: {network_name}")
                subprocess.run(
                    ["docker", "network", "create", network_name],
                    capture_output=True,
                    check=True
                )
        except Exception as e:
            logger.warning(f"Failed to create Docker network: {e}")
