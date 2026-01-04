"""
Kubernetes pod monitoring using kubectl top and metrics-server.

Collects CPU and memory metrics for Trino pods in a Kubernetes cluster.
"""

import re
import logging
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import MetricCollector, Metric, MetricType, MonitoringConfig

logger = logging.getLogger(__name__)


@dataclass
class PodMetrics:
    """Container for Kubernetes pod resource metrics."""
    timestamp: datetime
    pod_name: str
    namespace: str
    
    # CPU metrics
    cpu_millicores: Optional[int]  # CPU in millicores (1000m = 1 core)
    cpu_cores: Optional[float]      # CPU in cores
    
    # Memory metrics
    memory_bytes: Optional[int]     # Memory in bytes
    memory_mb: Optional[float]      # Memory in MB
    memory_gb: Optional[float]      # Memory in GB
    
    # Labels for pod identification
    labels: Dict[str, str]
    
    def to_metrics(self) -> List[Metric]:
        """Convert to list of Metric objects."""
        metrics = []
        base_labels = {
            "pod": self.pod_name,
            "namespace": self.namespace,
            **self.labels
        }
        
        # CPU metrics
        if self.cpu_millicores is not None:
            metrics.append(Metric(
                timestamp=self.timestamp,
                metric_type=MetricType.SYSTEM_RESOURCE,
                name="pod_cpu_millicores",
                value=self.cpu_millicores,
                unit="millicores",
                labels=base_labels.copy()
            ))
        
        if self.cpu_cores is not None:
            metrics.append(Metric(
                timestamp=self.timestamp,
                metric_type=MetricType.SYSTEM_RESOURCE,
                name="pod_cpu_cores",
                value=self.cpu_cores,
                unit="cores",
                labels=base_labels.copy()
            ))
        
        # Memory metrics
        if self.memory_bytes is not None:
            metrics.append(Metric(
                timestamp=self.timestamp,
                metric_type=MetricType.SYSTEM_RESOURCE,
                name="pod_memory_bytes",
                value=self.memory_bytes,
                unit="bytes",
                labels=base_labels.copy()
            ))
        
        if self.memory_mb is not None:
            metrics.append(Metric(
                timestamp=self.timestamp,
                metric_type=MetricType.SYSTEM_RESOURCE,
                name="pod_memory_mb",
                value=self.memory_mb,
                unit="MB",
                labels=base_labels.copy()
            ))
        
        if self.memory_gb is not None:
            metrics.append(Metric(
                timestamp=self.timestamp,
                metric_type=MetricType.SYSTEM_RESOURCE,
                name="pod_memory_gb",
                value=self.memory_gb,
                unit="GB",
                labels=base_labels.copy()
            ))
        
        return metrics


class KubernetesPodMonitor(MetricCollector):
    """
    Collects pod resource metrics from Kubernetes using kubectl top.
    
    Requires:
    - kubectl CLI installed and configured
    - metrics-server deployed in Kubernetes cluster
    - Access to cluster with proper context
    
    Monitors:
    - Pod CPU usage (millicores and cores)
    - Pod memory usage (bytes, MB, GB)
    - Supports filtering by namespace and labels
    """
    
    def __init__(self, 
                 config: MonitoringConfig,
                 context: str = "kind-tribench",
                 namespace: str = "default",
                 label_selector: Optional[str] = None,
                 pod_name_pattern: Optional[str] = None):
        """
        Initialize Kubernetes pod monitor.
        
        Args:
            config: Monitoring configuration
            context: Kubernetes context name
            namespace: Namespace to monitor
            label_selector: Label selector (e.g., "app=trino")
            pod_name_pattern: Regex pattern to match pod names
        """
        super().__init__(config)
        self.context = context
        self.namespace = namespace
        self.label_selector = label_selector
        self.pod_name_pattern = pod_name_pattern
        self._metrics_server_available = False
        
    def start(self) -> None:
        """Start Kubernetes pod monitoring."""
        # Verify kubectl is available
        try:
            subprocess.run(
                ["kubectl", "version", "--client"],
                capture_output=True,
                check=True
            )
            logger.info("kubectl CLI verified")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"kubectl not available: {e}")
            self.enabled = False
            return
        
        # Verify cluster connectivity
        try:
            subprocess.run(
                ["kubectl", "--context", self.context, "cluster-info"],
                capture_output=True,
                check=True,
                text=True
            )
            logger.info(f"Connected to Kubernetes cluster: {self.context}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Cannot connect to cluster '{self.context}': {e}")
            self.enabled = False
            return
        
        # Verify metrics-server is available
        self._metrics_server_available = self._check_metrics_server()
        if not self._metrics_server_available:
            logger.error("metrics-server not available in cluster")
            logger.error("Install with: kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml")
            self.enabled = False
            return
        
        logger.info(f"Kubernetes pod monitor started for namespace: {self.namespace}")
        if self.label_selector:
            logger.info(f"Filtering pods by labels: {self.label_selector}")
        if self.pod_name_pattern:
            logger.info(f"Filtering pods by pattern: {self.pod_name_pattern}")
    
    def stop(self) -> None:
        """Stop Kubernetes pod monitoring."""
        logger.info("Kubernetes pod monitor stopped")
    
    def _check_metrics_server(self) -> bool:
        """
        Check if metrics-server is deployed and responsive.
        
        Returns:
            True if metrics-server is available
        """
        try:
            # Try to get pod metrics - this will fail if metrics-server is not available
            result = subprocess.run(
                ["kubectl", "--context", self.context, "--namespace", self.namespace, "top", "pods"],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            # If we get "error: Metrics API not available", metrics-server is missing
            if "Metrics API not available" in result.stderr or "metrics not available" in result.stderr.lower():
                logger.warning("metrics-server API not available")
                return False
            
            # If command succeeded or failed with other error, metrics-server exists
            logger.info("metrics-server is available")
            return True
            
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking metrics-server availability")
            return False
        except Exception as e:
            logger.warning(f"Error checking metrics-server: {e}")
            return False
    
    def collect(self) -> List[Metric]:
        """
        Collect pod resource metrics using kubectl top.
        
        Returns:
            List of collected metrics
        """
        if not self.enabled or not self._metrics_server_available:
            return []
        
        timestamp = datetime.now()
        metrics = []
        
        try:
            # Get pod metrics
            pod_metrics_list = self._get_pod_metrics(timestamp)
            
            # Convert to Metric objects
            for pod_metrics in pod_metrics_list:
                metrics.extend(pod_metrics.to_metrics())
            
            logger.debug(f"Collected metrics for {len(pod_metrics_list)} pods")
            
        except Exception as e:
            logger.error(f"Error collecting Kubernetes pod metrics: {e}")
        
        return metrics
    
    def _get_pod_metrics(self, timestamp: datetime) -> List[PodMetrics]:
        """
        Execute kubectl top pods and parse output.
        
        Args:
            timestamp: Timestamp for metrics
            
        Returns:
            List of PodMetrics objects
        """
        try:
            # Build kubectl command
            cmd = [
                "kubectl", "--context", self.context,
                "--namespace", self.namespace,
                "top", "pods"
            ]
            
            # Add label selector if specified
            if self.label_selector:
                cmd.extend(["--selector", self.label_selector])
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                text=True,
                timeout=10
            )
            
            # Parse output
            return self._parse_kubectl_top_output(result.stdout, timestamp)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"kubectl top failed: {e.stderr}")
            return []
        except subprocess.TimeoutExpired:
            logger.error("kubectl top command timed out")
            return []
        except Exception as e:
            logger.error(f"Error getting pod metrics: {e}")
            return []
    
    def _parse_kubectl_top_output(self, output: str, timestamp: datetime) -> List[PodMetrics]:
        """
        Parse kubectl top pods output.
        
        Expected format:
        NAME                           CPU(cores)   MEMORY(bytes)
        trino-coordinator-abc123       150m         2048Mi
        trino-worker-1-def456          500m         4096Mi
        
        Args:
            output: kubectl top pods output
            timestamp: Timestamp for metrics
            
        Returns:
            List of PodMetrics objects
        """
        pod_metrics_list = []
        lines = output.strip().split('\n')
        
        if len(lines) < 2:
            # No pods or header only
            return []
        
        # Skip header line
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 3:
                continue
            
            pod_name = parts[0]
            cpu_str = parts[1]
            memory_str = parts[2]
            
            # Apply pod name filtering if specified
            if self.pod_name_pattern:
                if not re.search(self.pod_name_pattern, pod_name):
                    continue
            
            # Parse CPU (e.g., "150m" or "1500m" or "1.5")
            cpu_millicores, cpu_cores = self._parse_cpu(cpu_str)
            
            # Parse memory (e.g., "2048Mi" or "1Gi")
            memory_bytes, memory_mb, memory_gb = self._parse_memory(memory_str)
            
            # Get pod labels (could be extended to fetch from kubectl get pod)
            labels = self._extract_pod_labels(pod_name)
            
            pod_metrics = PodMetrics(
                timestamp=timestamp,
                pod_name=pod_name,
                namespace=self.namespace,
                cpu_millicores=cpu_millicores,
                cpu_cores=cpu_cores,
                memory_bytes=memory_bytes,
                memory_mb=memory_mb,
                memory_gb=memory_gb,
                labels=labels
            )
            
            pod_metrics_list.append(pod_metrics)
        
        return pod_metrics_list
    
    def _parse_cpu(self, cpu_str: str) -> tuple[Optional[int], Optional[float]]:
        """
        Parse CPU value from kubectl output.
        
        Examples:
        - "150m" -> (150, 0.15)
        - "1500m" -> (1500, 1.5)
        - "2" -> (2000, 2.0)
        
        Args:
            cpu_str: CPU string from kubectl
            
        Returns:
            Tuple of (millicores, cores)
        """
        try:
            if cpu_str.endswith('m'):
                # Millicores
                millicores = int(cpu_str[:-1])
                cores = millicores / 1000.0
                return millicores, cores
            else:
                # Cores
                cores = float(cpu_str)
                millicores = int(cores * 1000)
                return millicores, cores
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse CPU value '{cpu_str}': {e}")
            return None, None
    
    def _parse_memory(self, memory_str: str) -> tuple[Optional[int], Optional[float], Optional[float]]:
        """
        Parse memory value from kubectl output.
        
        Examples:
        - "2048Mi" -> (2147483648, 2048.0, 2.0)
        - "1Gi" -> (1073741824, 1024.0, 1.0)
        - "500Ki" -> (512000, 0.5, 0.0005)
        
        Args:
            memory_str: Memory string from kubectl
            
        Returns:
            Tuple of (bytes, MB, GB)
        """
        try:
            # Extract number and unit
            match = re.match(r'^(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|K|M|G|T)?$', memory_str)
            if not match:
                raise ValueError(f"Invalid memory format: {memory_str}")
            
            value = float(match.group(1))
            unit = match.group(2) or ''
            
            # Convert to bytes
            multipliers = {
                'Ki': 1024,
                'Mi': 1024 ** 2,
                'Gi': 1024 ** 3,
                'Ti': 1024 ** 4,
                'K': 1000,
                'M': 1000 ** 2,
                'G': 1000 ** 3,
                'T': 1000 ** 4,
            }
            
            multiplier = multipliers.get(unit, 1)
            bytes_value = int(value * multiplier)
            mb_value = bytes_value / (1024 ** 2)
            gb_value = bytes_value / (1024 ** 3)
            
            return bytes_value, mb_value, gb_value
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse memory value '{memory_str}': {e}")
            return None, None, None
    
    def _extract_pod_labels(self, pod_name: str) -> Dict[str, str]:
        """
        Extract useful labels from pod name.
        
        Args:
            pod_name: Kubernetes pod name
            
        Returns:
            Dictionary of labels
        """
        labels = {}
        
        # Identify Trino components from pod name
        if 'coordinator' in pod_name.lower():
            labels['component'] = 'coordinator'
            labels['role'] = 'coordinator'
        elif 'worker' in pod_name.lower():
            labels['component'] = 'worker'
            labels['role'] = 'worker'
        
        # Identify system
        if 'trino' in pod_name.lower():
            labels['system'] = 'trino'
        elif 'minio' in pod_name.lower():
            labels['system'] = 'minio'
        elif 'postgres' in pod_name.lower():
            labels['system'] = 'postgres'
        elif 'hive' in pod_name.lower():
            labels['system'] = 'hive-metastore'
        
        return labels
    
    def get_pod_list(self) -> List[str]:
        """
        Get list of pod names currently being monitored.
        
        Returns:
            List of pod names
        """
        try:
            cmd = [
                "kubectl", "--context", self.context,
                "--namespace", self.namespace,
                "get", "pods", "-o", "name"
            ]
            
            if self.label_selector:
                cmd.extend(["--selector", self.label_selector])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                text=True
            )
            
            # Parse output (format: "pod/name")
            pods = [line.split('/')[-1] for line in result.stdout.strip().split('\n') if line]
            
            # Apply pattern filter
            if self.pod_name_pattern:
                pods = [p for p in pods if re.search(self.pod_name_pattern, p)]
            
            return pods
            
        except Exception as e:
            logger.error(f"Error getting pod list: {e}")
            return []
