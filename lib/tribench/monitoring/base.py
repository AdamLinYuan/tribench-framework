"""
Base classes for monitoring infrastructure.

Defines abstract interfaces and common data structures for metric collection,
storage, and monitoring session management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import logging
import threading
import time

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    SYSTEM_RESOURCE = "system_resource"
    TRINO_JMX = "trino_jmx"
    QUERY_EXECUTION = "query_execution"
    CUSTOM = "custom"


@dataclass
class MonitoringConfig:
    """Configuration for monitoring session."""
    
    # General settings
    enabled: bool = True
    interval_seconds: float = 1.0
    output_dir: str = "results/monitoring"
    
    # Resource monitoring
    collect_system_resources: bool = True
    collect_per_core_cpu: bool = True
    collect_disk_io: bool = True
    collect_network_io: bool = True
    
    # Trino monitoring
    collect_trino_jmx: bool = True
    collect_query_plans: bool = True
    trino_jmx_port: int = 8080
    
    # Storage settings
    store_timeseries: bool = True
    export_csv: bool = True
    export_json: bool = True
    
    # Alert settings
    enable_alerts: bool = False
    alert_thresholds: Dict[str, Any] = field(default_factory=dict)
    
    # Performance
    buffer_size: int = 1000  # Number of samples to buffer before writing
    

@dataclass
class Metric:
    """Single metric data point."""
    timestamp: datetime
    metric_type: MetricType
    name: str
    value: Any
    unit: str
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'metric_type': self.metric_type.value,
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'labels': self.labels
        }


class MetricCollector(ABC):
    """
    Abstract base class for metric collectors.
    
    Collectors are responsible for gathering specific types of metrics
    (system resources, JMX, queries, etc.) at regular intervals.
    """
    
    def __init__(self, config: MonitoringConfig):
        """
        Initialize metric collector.
        
        Args:
            config: Monitoring configuration
        """
        self.config = config
        self.enabled = True
        self._metrics_buffer: List[Metric] = []
        
    @abstractmethod
    def collect(self) -> List[Metric]:
        """
        Collect metrics at current point in time.
        
        Returns:
            List of collected metrics
        """
        pass
    
    @abstractmethod
    def start(self) -> None:
        """Start the collector (e.g., connect to services)."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the collector and cleanup resources."""
        pass
    
    def is_enabled(self) -> bool:
        """Check if collector is enabled."""
        return self.enabled and self.config.enabled
    
    def buffer_metrics(self, metrics: List[Metric]) -> None:
        """Add metrics to internal buffer."""
        self._metrics_buffer.extend(metrics)
    
    def flush_buffer(self) -> List[Metric]:
        """Return and clear buffered metrics."""
        metrics = self._metrics_buffer.copy()
        self._metrics_buffer.clear()
        return metrics


class MonitoringSession:
    """
    Orchestrates metric collection during an experiment.
    
    Manages multiple collectors, coordinates data collection,
    and handles storage of collected metrics.
    """
    
    def __init__(self, 
                 config: MonitoringConfig,
                 experiment_name: str,
                 collectors: Optional[List[MetricCollector]] = None):
        """
        Initialize monitoring session.
        
        Args:
            config: Monitoring configuration
            experiment_name: Name of experiment being monitored
            collectors: List of metric collectors to use
        """
        self.config = config
        self.experiment_name = experiment_name
        self.collectors = collectors or []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.is_running = False
        
        # Collection thread management
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._collected_metrics: List[Metric] = []
        self._metrics_lock = threading.Lock()
        
        logger.info(f"Monitoring session initialized for experiment: {experiment_name}")
    
    def add_collector(self, collector: MetricCollector) -> None:
        """Add a metric collector to the session."""
        self.collectors.append(collector)
        logger.debug(f"Added collector: {collector.__class__.__name__}")
    
    def start(self) -> None:
        """Start monitoring session."""
        if self.is_running:
            logger.warning("Monitoring session already running")
            return
        
        self.start_time = datetime.now()
        self.is_running = True
        self._stop_event.clear()
        
        # Start all collectors
        for collector in self.collectors:
            if collector.is_enabled():
                try:
                    collector.start()
                    logger.info(f"Started collector: {collector.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Failed to start collector {collector.__class__.__name__}: {e}")
        
        # Start collection thread
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            name=f"MonitoringSession-{self.experiment_name}",
            daemon=True
        )
        self._collection_thread.start()
        
        logger.info(f"Monitoring session started at {self.start_time}")
    
    def _collection_loop(self) -> None:
        """Background thread that periodically collects metrics."""
        logger.debug(f"Collection thread started (interval: {self.config.interval_seconds}s)")
        
        while not self._stop_event.is_set():
            try:
                # Collect metrics from all collectors
                metrics = self.collect_metrics()
                
                # Store collected metrics
                with self._metrics_lock:
                    self._collected_metrics.extend(metrics)
                
                # Also store in each collector's buffer for compatibility
                for collector in self.collectors:
                    if collector.is_enabled() and hasattr(collector, '_metrics_buffer'):
                        collector._metrics_buffer.extend([m for m in metrics if m.metric_type.value in str(collector.__class__.__name__).lower() or m.metric_type == MetricType.SYSTEM_RESOURCE])
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
            
            # Wait for next collection interval or stop event
            self._stop_event.wait(self.config.interval_seconds)
        
        logger.debug("Collection thread stopped")
    
    def collect_metrics(self) -> List[Metric]:
        """
        Collect metrics from all enabled collectors.
        
        Returns:
            List of collected metrics from all collectors
        """
        all_metrics = []
        
        for collector in self.collectors:
            if collector.is_enabled():
                try:
                    metrics = collector.collect()
                    all_metrics.extend(metrics)
                except Exception as e:
                    logger.error(f"Error collecting metrics from {collector.__class__.__name__}: {e}")
        
        return all_metrics
    
    def stop(self) -> None:
        """Stop monitoring session."""
        if not self.is_running:
            logger.warning("Monitoring session not running")
            return
        
        # Signal collection thread to stop
        self._stop_event.set()
        
        # Wait for collection thread to finish
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5.0)
            if self._collection_thread.is_alive():
                logger.warning("Collection thread did not stop gracefully")
        
        self.end_time = datetime.now()
        self.is_running = False
        
        # Stop all collectors
        for collector in self.collectors:
            try:
                collector.stop()
                logger.info(f"Stopped collector: {collector.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error stopping collector {collector.__class__.__name__}: {e}")
        
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Monitoring session stopped. Duration: {duration:.2f}s")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of monitoring session.
        
        Returns:
            Dictionary with session statistics
        """
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            'experiment_name': self.experiment_name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': duration,
            'collectors_count': len(self.collectors),
            'collectors': [c.__class__.__name__ for c in self.collectors],
            'is_running': self.is_running
        }
    
    def save_metrics(self) -> Optional[str]:
        """
        Save metrics from all collectors that have storage.
        
        Returns:
            Path to saved metrics file, or None if no metrics saved
        """
        # Get all collected metrics from session
        with self._metrics_lock:
            all_metrics = self._collected_metrics.copy()
        
        # Also collect any remaining metrics from collector buffers
        for collector in self.collectors:
            if hasattr(collector, '_metrics_buffer') and collector._metrics_buffer:
                all_metrics.extend(collector._metrics_buffer)
        
        if not all_metrics:
            logger.warning("No metrics collected to save")
            return None
        
        # Import storage here to avoid circular dependency
        from .storage import MetricsStorage, TimeSeriesData
        
        # Save to storage
        storage = MetricsStorage(storage_dir=self.config.output_dir)
        timeseries_data = TimeSeriesData(
            experiment_name=self.experiment_name,
            start_time=self.start_time if self.start_time else datetime.now(),
            end_time=self.end_time if self.end_time else datetime.now(),
            metrics=all_metrics
        )
        
        saved_file = storage.save_timeseries(timeseries_data)
        logger.info(f"Saved {len(all_metrics)} metrics to {saved_file}")
        
        return saved_file

