"""
Kind cluster management operations.

Handles creation, deletion, and status checking of Kind Kubernetes clusters.
"""

import json
import logging
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class KindClusterManager:
    """Manages Kind Kubernetes cluster lifecycle."""
    
    def __init__(self, cluster_name: str, context: str, kind_config: Path):
        """
        Initialize Kind cluster manager.
        
        Args:
            cluster_name: Name of the Kind cluster
            context: Kubernetes context name
            kind_config: Path to Kind cluster configuration file
        """
        self.cluster_name = cluster_name
        self.context = context
        self.kind_config = Path(kind_config)
    
    def exists(self) -> bool:
        """Check if the Kind cluster exists."""
        try:
            result = subprocess.run(
                ["kind", "get", "clusters"],
                capture_output=True,
                text=True,
                check=True
            )
            clusters = result.stdout.strip().split('\n')
            return self.cluster_name in clusters
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def status(self) -> Dict[str, Any]:
        """
        Get detailed cluster status.
        
        Returns:
            Dictionary with cluster info including nodes, their roles, and status
        """
        status = {
            "exists": False,
            "running": False,
            "nodes": [],
            "config_file": str(self.kind_config),
            "cluster_name": self.cluster_name,
        }
        
        if not self.exists():
            return status
        
        status["exists"] = True
        
        try:
            # Get node information
            result = subprocess.run(
                ["kubectl", "--context", self.context, "get", "nodes", "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            nodes_data = json.loads(result.stdout)
            
            for node in nodes_data.get("items", []):
                node_name = node["metadata"]["name"]
                labels = node["metadata"].get("labels", {})
                
                # Determine role from labels
                role = "worker"
                if "node-role.kubernetes.io/control-plane" in labels:
                    role = "control-plane"
                
                # Get status conditions
                conditions = node["status"].get("conditions", [])
                ready = any(c["type"] == "Ready" and c["status"] == "True" for c in conditions)
                
                status["nodes"].append({
                    "name": node_name,
                    "role": role,
                    "ready": ready,
                })
            
            # Cluster is running if we have nodes
            status["running"] = len(status["nodes"]) > 0 and all(n["ready"] for n in status["nodes"])
            
            # Compare with expected config
            if self.kind_config.exists():
                expected = self._parse_kind_config()
                status["expected_nodes"] = expected
                status["config_matches"] = self._config_matches(status["nodes"], expected)
            
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def _parse_kind_config(self) -> Dict[str, int]:
        """Parse Kind config to get expected node counts."""
        import yaml
        
        expected = {"control-plane": 0, "worker": 0}
        
        if not self.kind_config.exists():
            return expected
        
        try:
            with open(self.kind_config) as f:
                config = yaml.safe_load(f)
            
            for node in config.get("nodes", []):
                role = node.get("role", "worker")
                if role == "control-plane":
                    expected["control-plane"] += 1
                else:
                    expected["worker"] += 1
                    
        except Exception as e:
            logger.warning(f"Failed to parse Kind config: {e}")
        
        return expected
    
    def _config_matches(self, actual_nodes: List[Dict], expected: Dict[str, int]) -> bool:
        """Check if actual nodes match expected configuration."""
        actual_counts = {"control-plane": 0, "worker": 0}
        for node in actual_nodes:
            role = node.get("role", "worker")
            if role in actual_counts:
                actual_counts[role] += 1
        
        return actual_counts == expected
    
    def create(self, force: bool = False) -> bool:
        """
        Create the Kind cluster using the configuration file.
        
        Args:
            force: If True, delete existing cluster first
            
        Returns:
            True if cluster was created successfully
        """
        logger.info(f"Creating Kind cluster '{self.cluster_name}'...")
        
        # Check if cluster already exists
        if self.exists():
            if force:
                logger.info("Force flag set, deleting existing cluster...")
                self.delete()
            else:
                logger.warning(f"Cluster '{self.cluster_name}' already exists. Use force=True to recreate.")
                return False
        
        # Verify config file exists
        if not self.kind_config.exists():
            raise FileNotFoundError(f"Kind config file not found: {self.kind_config}")
        
        # Create cluster with config
        cmd = [
            "kind", "create", "cluster",
            "--name", self.cluster_name,
            "--config", str(self.kind_config)
        ]
        
        try:
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(result.stdout)
            logger.info(f"✓ Kind cluster '{self.cluster_name}' created successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create cluster: {e.stderr}")
            raise RuntimeError(f"Failed to create Kind cluster: {e.stderr}")
    
    def delete(self) -> bool:
        """
        Delete the Kind cluster.
        
        Returns:
            True if cluster was deleted successfully
        """
        logger.info(f"Deleting Kind cluster '{self.cluster_name}'...")
        
        if not self.exists():
            logger.info(f"Cluster '{self.cluster_name}' does not exist")
            return True
        
        cmd = ["kind", "delete", "cluster", "--name", self.cluster_name]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"✓ Kind cluster '{self.cluster_name}' deleted")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete cluster: {e.stderr}")
            raise RuntimeError(f"Failed to delete Kind cluster: {e.stderr}")
    
    def ensure(self) -> bool:
        """
        Ensure the Kind cluster exists and matches the expected configuration.
        
        If the cluster doesn't exist, creates it.
        If the cluster exists but doesn't match config, offers to recreate.
        
        Returns:
            True if cluster is ready
        """
        status = self.status()
        
        if not status["exists"]:
            logger.info("Cluster does not exist, creating...")
            return self.create()
        
        if not status.get("config_matches", True):
            expected = status.get("expected_nodes", {})
            actual_nodes = status.get("nodes", [])
            
            actual_counts = {"control-plane": 0, "worker": 0}
            for node in actual_nodes:
                role = node.get("role", "worker")
                if role in actual_counts:
                    actual_counts[role] += 1
            
            logger.warning(
                f"Cluster configuration mismatch:\n"
                f"  Expected: {expected['control-plane']} control-plane, {expected['worker']} worker nodes\n"
                f"  Actual: {actual_counts['control-plane']} control-plane, {actual_counts['worker']} worker nodes"
            )
            return False  # Return False to indicate mismatch - caller can decide to recreate
        
        logger.info(f"Cluster '{self.cluster_name}' exists and matches configuration")
        return True
