"""
Kubernetes operations using kubectl.

Provides kubectl command execution and resource management.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class KubectlOperator:
    """Handles kubectl command execution and resource management."""
    
    def __init__(self, context: str, namespace: str):
        """
        Initialize kubectl operator.
        
        Args:
            context: Kubernetes context name
            namespace: Default namespace for operations
        """
        self.context = context
        self.namespace = namespace
    
    def run(self, args: List[str], namespace: Optional[str] = None, 
            check: bool = True, log_errors: bool = True) -> str:
        """
        Execute kubectl command.
        
        Args:
            args: kubectl command arguments
            namespace: Override namespace (None for cluster-wide)
            check: Whether to raise on error
            log_errors: Whether to log errors
        
        Returns:
            Command output (stdout)
        """
        cmd = ["kubectl", "--context", self.context]
        
        # Use configured namespace unless explicitly overridden or set to None (cluster-wide)
        ns = namespace if namespace is not None else self.namespace
        if ns:
            cmd.extend(["--namespace", ns])
        
        cmd.extend(args)
        
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if log_errors:
                logger.error(f"Command failed: {' '.join(cmd)}")
                logger.error(f"Stdout: {e.stdout}")
                logger.error(f"Stderr: {e.stderr}")
            raise
    
    def ensure_namespace(self) -> None:
        """Ensure the configured namespace exists."""
        try:
            self.run(["get", "namespace", self.namespace], namespace="")
        except subprocess.CalledProcessError:
            logger.info(f"Creating namespace '{self.namespace}'")
            self.run(["create", "namespace", self.namespace], namespace="")
    
    def verify_cluster(self) -> None:
        """Verify cluster connection."""
        try:
            self.run(["cluster-info"], namespace="")
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Cannot connect to Kubernetes cluster with context '{self.context}'")
    
    def apply_manifest(self, manifest_path: Path) -> None:
        """Apply a Kubernetes manifest."""
        self.run(["apply", "-f", str(manifest_path)])
    
    def delete_manifest(self, manifest_path: Path, log_errors: bool = False) -> None:
        """Delete resources from a manifest."""
        try:
            self.run(["delete", "-f", str(manifest_path)], log_errors=log_errors)
        except subprocess.CalledProcessError:
            pass
    
    def scale_deployment(self, deployment: str, replicas: int, log_errors: bool = False) -> None:
        """Scale a deployment to specified replica count."""
        try:
            self.run(["scale", "deployment", deployment, f"--replicas={replicas}"], log_errors=log_errors)
        except subprocess.CalledProcessError:
            pass
    
    def wait_for_rollout(self, resource: str, log_errors: bool = True) -> None:
        """Wait for deployment rollout to complete."""
        try:
            self.run(["rollout", "status", resource], log_errors=log_errors)
        except subprocess.CalledProcessError:
            pass
    
    def exec_in_pod(self, deployment: str, command: List[str]) -> str:
        """
        Execute command in a pod.
        
        Args:
            deployment: Deployment name
            command: Command to execute
        
        Returns:
            Command output
        """
        args = ["exec", f"deployment/{deployment}", "--"] + command
        return self.run(args)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get cluster status including pods and services.
        
        Returns:
            Status dictionary with pods and services
        """
        status = {
            "running": False,
            "pods": [],
            "services": []
        }
        
        try:
            # Get Pods
            pods_json = self.run(["get", "pods", "-o", "json"])
            pods = json.loads(pods_json)
            
            trino_running = False
            
            for pod in pods.get("items", []):
                pod_name = pod["metadata"]["name"]
                pod_phase = pod["status"]["phase"]
                is_ready = all(c["ready"] for c in pod["status"].get("containerStatuses", []))
                
                status["pods"].append({
                    "name": pod_name,
                    "status": pod_phase,
                    "ready": is_ready
                })
                
                if "trino" in pod_name and pod_phase == "Running":
                    trino_running = True
            
            # Get Services
            svc_json = self.run(["get", "svc", "-o", "json"])
            svcs = json.loads(svc_json)
            for svc in svcs.get("items", []):
                status["services"].append({
                    "name": svc["metadata"]["name"],
                    "type": svc["spec"]["type"],
                    "ports": svc["spec"]["ports"]
                })
            
            status["running"] = trino_running
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def ensure_bucket(self, deployment: str, bucket_name: str) -> bool:
        """
        Ensure a MinIO bucket exists.
        
        Args:
            deployment: MinIO deployment name
            bucket_name: Bucket name to create
        
        Returns:
            True if bucket exists or was created
        """
        logger.info(f"Ensuring MinIO bucket '{bucket_name}' exists...")
        
        try:
            # Create bucket directory with proper permissions
            self.exec_in_pod(deployment, ["sh", "-c", f"mkdir -p /data/{bucket_name} && chmod 777 /data/{bucket_name}"])
            
            # Verify bucket was created
            result = self.exec_in_pod(deployment, ["ls", "-d", f"/data/{bucket_name}"])
            if bucket_name in result:
                logger.info(f"✓ MinIO bucket '{bucket_name}' ready")
                return True
            else:
                logger.warning(f"Bucket '{bucket_name}' creation may have failed")
                return False
        except Exception as e:
            logger.error(f"Failed to create MinIO bucket '{bucket_name}': {e}")
            return False
