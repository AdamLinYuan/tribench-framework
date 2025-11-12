"""
System resource monitoring using psutil and docker stats.

Collects CPU, memory, disk I/O, and network I/O metrics at regular intervals.
"""

import psutil
import docker
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .base import MetricCollector, Metric, MetricType, MonitoringConfig

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Container for system resource metrics."""
    timestamp: datetime
    
    # CPU metrics
    cpu_percent_total: float
    cpu_percent_per_core: List[float]
    cpu_count: int
    
    # Memory metrics
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_percent: float
    
    # Disk I/O metrics
    disk_read_mb: float
    disk_write_mb: float
    disk_read_count: int
    disk_write_count: int
    
    # Network I/O metrics
    network_sent_mb: float
    network_recv_mb: float
    network_packets_sent: int
    network_packets_recv: int
    
    def to_metrics(self) -> List[Metric]:
        """Convert to list of Metric objects."""
        metrics = []
        
        # CPU metrics
        metrics.append(Metric(
            timestamp=self.timestamp,
            metric_type=MetricType.SYSTEM_RESOURCE,
            name="cpu_percent_total",
            value=self.cpu_percent_total,
            unit="percent"
        ))
        
        for i, cpu_pct in enumerate(self.cpu_percent_per_core):
            metrics.append(Metric(
                timestamp=self.timestamp,
                metric_type=MetricType.SYSTEM_RESOURCE,
                name="cpu_percent",
                value=cpu_pct,
                unit="percent",
                labels={"core": str(i)}
            ))
        
        # Memory metrics
        metrics.extend([
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "memory_used", self.memory_used_gb, "GB"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "memory_percent", self.memory_percent, "percent"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "swap_used", self.swap_used_gb, "GB"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "swap_percent", self.swap_percent, "percent"),
        ])
        
        # Disk I/O metrics
        metrics.extend([
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "disk_read", self.disk_read_mb, "MB"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "disk_write", self.disk_write_mb, "MB"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "disk_read_count", self.disk_read_count, "operations"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "disk_write_count", self.disk_write_count, "operations"),
        ])
        
        # Network I/O metrics
        metrics.extend([
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "network_sent", self.network_sent_mb, "MB"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "network_recv", self.network_recv_mb, "MB"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "network_packets_sent", self.network_packets_sent, "packets"),
            Metric(self.timestamp, MetricType.SYSTEM_RESOURCE, "network_packets_recv", self.network_packets_recv, "packets"),
        ])
        
        return metrics


class ResourceMonitor(MetricCollector):
    """
    Collects system resource metrics using psutil.
    
    Monitors:
    - CPU utilization (total and per-core)
    - Memory usage (RAM and swap)
    - Disk I/O (read/write bytes and operations)
    - Network I/O (sent/received bytes and packets)
    """
    
    def __init__(self, config: MonitoringConfig):
        """
        Initialize resource monitor.
        
        Args:
            config: Monitoring configuration
        """
        super().__init__(config)
        self._baseline_disk_io: Optional[Any] = None
        self._baseline_network_io: Optional[Any] = None
        self._docker_client: Optional[docker.DockerClient] = None
        self._monitored_containers: List[str] = []
        
    def start(self) -> None:
        """Start resource monitoring."""
        # Initialize Docker client if available
        try:
            self._docker_client = docker.from_env()
            logger.info("Docker client initialized for container monitoring")
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
            self._docker_client = None
        
        # Capture baseline I/O counters
        if self.config.collect_disk_io:
            self._baseline_disk_io = psutil.disk_io_counters()
        
        if self.config.collect_network_io:
            self._baseline_network_io = psutil.net_io_counters()
        
        logger.info("Resource monitor started")
    
    def stop(self) -> None:
        """Stop resource monitoring."""
        if self._docker_client:
            self._docker_client.close()
        logger.info("Resource monitor stopped")
    
    def add_container(self, container_name: str) -> None:
        """Add container to monitor."""
        if container_name not in self._monitored_containers:
            self._monitored_containers.append(container_name)
            logger.debug(f"Added container to monitor: {container_name}")
    
    def collect(self) -> List[Metric]:
        """
        Collect system resource metrics.
        
        Returns:
            List of collected metrics
        """
        timestamp = datetime.now()
        metrics = []
        
        try:
            # Collect system-wide metrics
            system_metrics = self._collect_system_metrics(timestamp)
            metrics.extend(system_metrics.to_metrics())
            
            # Collect per-container metrics
            if self._docker_client and self._monitored_containers:
                container_metrics = self._collect_container_metrics(timestamp)
                metrics.extend(container_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}")
        
        return metrics
    
    def _collect_system_metrics(self, timestamp: datetime) -> SystemMetrics:
        """Collect system-wide resource metrics."""
        # CPU metrics
        cpu_percent_total = psutil.cpu_percent(interval=0)
        cpu_percent_per_core = psutil.cpu_percent(interval=0, percpu=True) if self.config.collect_per_core_cpu else []
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk I/O metrics
        disk_read_mb = 0.0
        disk_write_mb = 0.0
        disk_read_count = 0
        disk_write_count = 0
        
        if self.config.collect_disk_io:
            disk_io = psutil.disk_io_counters()
            if disk_io and self._baseline_disk_io:
                disk_read_mb = (disk_io.read_bytes - self._baseline_disk_io.read_bytes) / (1024 * 1024)
                disk_write_mb = (disk_io.write_bytes - self._baseline_disk_io.write_bytes) / (1024 * 1024)
                disk_read_count = disk_io.read_count - self._baseline_disk_io.read_count
                disk_write_count = disk_io.write_count - self._baseline_disk_io.write_count
        
        # Network I/O metrics
        network_sent_mb = 0.0
        network_recv_mb = 0.0
        network_packets_sent = 0
        network_packets_recv = 0
        
        if self.config.collect_network_io:
            net_io = psutil.net_io_counters()
            if net_io and self._baseline_network_io:
                network_sent_mb = (net_io.bytes_sent - self._baseline_network_io.bytes_sent) / (1024 * 1024)
                network_recv_mb = (net_io.bytes_recv - self._baseline_network_io.bytes_recv) / (1024 * 1024)
                network_packets_sent = net_io.packets_sent - self._baseline_network_io.packets_sent
                network_packets_recv = net_io.packets_recv - self._baseline_network_io.packets_recv
        
        return SystemMetrics(
            timestamp=timestamp,
            cpu_percent_total=cpu_percent_total,
            cpu_percent_per_core=cpu_percent_per_core,
            cpu_count=cpu_count,
            memory_total_gb=memory.total / (1024**3),
            memory_used_gb=memory.used / (1024**3),
            memory_percent=memory.percent,
            swap_total_gb=swap.total / (1024**3),
            swap_used_gb=swap.used / (1024**3),
            swap_percent=swap.percent,
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            disk_read_count=disk_read_count,
            disk_write_count=disk_write_count,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            network_packets_sent=network_packets_sent,
            network_packets_recv=network_packets_recv
        )
    
    def _collect_container_metrics(self, timestamp: datetime) -> List[Metric]:
        """Collect per-container resource metrics using Docker stats."""
        metrics = []
        
        if not self._docker_client:
            return metrics
        
        for container_name in self._monitored_containers:
            try:
                container = self._docker_client.containers.get(container_name)
                stats = container.stats(stream=False)
                
                # Parse CPU stats
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                cpu_percent = 0.0
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100.0
                
                metrics.append(Metric(
                    timestamp=timestamp,
                    metric_type=MetricType.SYSTEM_RESOURCE,
                    name="container_cpu_percent",
                    value=cpu_percent,
                    unit="percent",
                    labels={"container": container_name}
                ))
                
                # Parse memory stats
                memory_usage_mb = stats['memory_stats']['usage'] / (1024 * 1024)
                memory_limit_mb = stats['memory_stats']['limit'] / (1024 * 1024)
                memory_percent = (memory_usage_mb / memory_limit_mb) * 100.0
                
                metrics.extend([
                    Metric(timestamp, MetricType.SYSTEM_RESOURCE, "container_memory_usage",
                          memory_usage_mb, "MB", {"container": container_name}),
                    Metric(timestamp, MetricType.SYSTEM_RESOURCE, "container_memory_percent",
                          memory_percent, "percent", {"container": container_name}),
                ])
                
                # Parse network stats
                if 'networks' in stats:
                    for network_name, network_stats in stats['networks'].items():
                        rx_mb = network_stats['rx_bytes'] / (1024 * 1024)
                        tx_mb = network_stats['tx_bytes'] / (1024 * 1024)
                        
                        metrics.extend([
                            Metric(timestamp, MetricType.SYSTEM_RESOURCE, "container_network_rx",
                                  rx_mb, "MB", {"container": container_name, "network": network_name}),
                            Metric(timestamp, MetricType.SYSTEM_RESOURCE, "container_network_tx",
                                  tx_mb, "MB", {"container": container_name, "network": network_name}),
                        ])
                
            except docker.errors.NotFound:
                logger.warning(f"Container not found: {container_name}")
            except Exception as e:
                logger.error(f"Error collecting metrics for container {container_name}: {e}")
        
        return metrics
