"""
Monitoring module for TriBench.

Provides resource monitoring, metrics collection, and performance tracking
for experiments and systems.
"""

from .base import (
    MetricCollector,
    Metric,
    MonitoringConfig,
    MonitoringSession,
)

from .resource_monitor import (
    ResourceMonitor,
    SystemMetrics,
)

from .trino_monitor import (
    TrinoMonitor,
    QueryMetrics,
    ClusterMetrics,
)

from .kubernetes_monitor import (
    KubernetesPodMonitor,
    PodMetrics,
)

from .storage import (
    MetricsStorage,
    TimeSeriesData,
)

from .alerts import (
    AlertManager,
    AlertThreshold,
    Alert,
    AlertSeverity,
    ThresholdCondition,
    create_memory_alert,
    create_cpu_alert,
    create_disk_space_alert,
    create_query_timeout_alert,
)

__all__ = [
    # Base classes
    "MetricCollector",
    "Metric",
    "MonitoringConfig",
    "MonitoringSession",
    
    # Resource monitoring
    "ResourceMonitor",
    "SystemMetrics",
    
    # Trino monitoring
    "TrinoMonitor",
    "QueryMetrics",
    "ClusterMetrics",
    
    # Kubernetes monitoring
    "KubernetesPodMonitor",
    "PodMetrics",
    
    # Storage
    "MetricsStorage",
    "TimeSeriesData",
    
    # Alerts
    "AlertManager",
    "AlertThreshold",
    "Alert",
    "AlertSeverity",
    "ThresholdCondition",
    "create_memory_alert",
    "create_cpu_alert",
    "create_disk_space_alert",
    "create_query_timeout_alert",
]
