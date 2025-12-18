"""
Port forwarding management for Kubernetes services.

Handles kubectl port-forward lifecycle and cleanup.
"""

import logging
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from tribench.defaults import Defaults

logger = logging.getLogger(__name__)


class PortForwarder:
    """Manages port forwarding for Kubernetes services."""
    
    def __init__(self, context: str, namespace: str, local_port: int, container_port: int):
        """
        Initialize port forwarder.
        
        Args:
            context: Kubernetes context
            namespace: Kubernetes namespace
            local_port: Local port to forward to
            container_port: Container port to forward from
        """
        self.context = context
        self.namespace = namespace
        self.local_port = local_port
        self.container_port = container_port
        self._process: Optional[subprocess.Popen] = None
        self.pid_file = Path("log/port-forward.pid")
        self.log_file = Path("log/port-forward.log")
    
    def is_active(self) -> bool:
        """Check if port forwarding is currently active."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((Defaults.Hosts.LOCALHOST, self.local_port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def ensure_active(self) -> bool:
        """
        Ensure port forwarding is active, starting it if necessary.
        
        Returns:
            True if port forwarding is now active, False otherwise
        """
        if self.is_active():
            logger.info(f"Port forwarding already active on port {self.local_port}")
            return True
        
        logger.info("Port forwarding not active, starting...")
        self.start()
        return self.is_active()
    
    def start(self, service_name: Optional[str] = None) -> None:
        """
        Start kubectl port-forward in the background and persist PID.
        
        Args:
            service_name: Name of the service to forward (defaults to Trino service)
        """
        # Check if already running
        if self.is_active():
            logger.info("Port forwarding already active")
            return
        
        # Clean up any stale processes
        self._cleanup_stale()
        
        if service_name is None:
            service_name = Defaults.ServiceNames.TRINO
        
        logger.info(f"Starting port forwarding {self.local_port}:{self.container_port}")
        
        cmd = [
            "kubectl", "--context", self.context, "--namespace", self.namespace,
            "port-forward", f"svc/{service_name}", 
            f"{self.local_port}:{self.container_port}"
        ]
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(exist_ok=True)
        pf_log = open(self.log_file, "w")
        
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=pf_log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True  # Detach from parent
            )
            # Give it a moment to start
            time.sleep(Defaults.Retry.PORT_FORWARD_STARTUP_DELAY)
            if self._process.poll() is not None:
                # It died immediately
                raise RuntimeError(f"Port forwarding failed to start. Check {self.log_file}")
            
            # Persist PID to file for cross-session access
            self.pid_file.write_text(str(self._process.pid))
            
            logger.info(f"Port forwarding started for service '{service_name}' (pid {self._process.pid})")
        except Exception as e:
            logger.error(f"Failed to start port forwarding: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the port forwarding process."""
        # Method 1: Stop from PID file (cross-session)
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                logger.info(f"Stopping port forwarding (pid {pid})")
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(Defaults.Retry.PROCESS_KILL_DELAY)
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    logger.debug(f"Process {pid} already dead")
                self.pid_file.unlink()
            except (ValueError, OSError) as e:
                logger.debug(f"Could not stop from PID file: {e}")
                self.pid_file.unlink(missing_ok=True)
        
        # Method 2: Stop the in-memory process (if this is the same session)
        if self._process:
            logger.info("Stopping port forwarding (child process)")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        
        # Method 3: Find any process holding the port (fallback)
        try:
            cmd = ["lsof", "-t", "-i", f":{self.local_port}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        logger.info(f"Killing process {pid} on port {self.local_port}")
                        subprocess.run(["kill", pid], check=False)
        except Exception as e:
            logger.debug(f"Failed to check for processes on port {self.local_port}: {e}")
    
    def _cleanup_stale(self) -> None:
        """Clean up any stale port forwarding processes."""
        # Try to kill process from PID file
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                # Check if process is still running
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    logger.info(f"Killing stale port-forward process {pid}")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(Defaults.Retry.PROCESS_KILL_DELAY)
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, signal.SIGKILL)  # Force kill if still alive
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass  # Process already dead
                self.pid_file.unlink()
            except (ValueError, OSError) as e:
                logger.debug(f"Could not clean up from PID file: {e}")
                self.pid_file.unlink(missing_ok=True)
