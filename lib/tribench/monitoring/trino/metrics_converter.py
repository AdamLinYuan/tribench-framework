"""
Metric conversion utilities.

Converts Trino metrics to standard Metric objects.
"""

from datetime import datetime
from typing import List

from tribench.monitoring.base import Metric, MetricType
from .models import QueryMetrics, ClusterMetrics


class MetricsConverter:
    """Converts Trino-specific metrics to standard Metric format."""
    
    @staticmethod
    def convert_cluster_metrics(cluster: ClusterMetrics, timestamp: datetime) -> List[Metric]:
        """
        Convert ClusterMetrics to list of Metric objects.
        
        Args:
            cluster: ClusterMetrics object
            timestamp: Collection timestamp
            
        Returns:
            List of Metric objects
        """
        labels = {
            "source": "trino_cluster",
            "version": cluster.version,
        }
        
        return [
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.queries.running",
                value=cluster.running_queries,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.queries.queued",
                value=cluster.queued_queries,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.queries.blocked",
                value=cluster.blocked_queries,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.nodes.active",
                value=cluster.active_nodes,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.drivers.running",
                value=cluster.running_drivers,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.tasks.running",
                value=cluster.running_tasks,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.memory.reserved",
                value=cluster.reserved_memory_bytes,
                unit="bytes",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                metric_type=MetricType.TRINO_JMX,
                name="trino.cluster.processors.available",
                value=cluster.total_available_processors,
                unit="count",
                labels=labels,
            ),
        ]
    
    @staticmethod
    def convert_query_metrics(query: QueryMetrics, timestamp: datetime) -> List[Metric]:
        """
        Convert QueryMetrics to list of Metric objects.
        
        Args:
            query: QueryMetrics object
            timestamp: Collection timestamp
            
        Returns:
            List of Metric objects
        """
        labels = {
            "source": "trino_query",
            "query_id": query.query_id,
            "state": query.state,
            "user": query.user or "unknown",
        }
        
        metrics = []
        
        # Timing metrics
        if query.queued_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.time.queued",
                value=query.queued_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.planning_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.time.planning",
                value=query.planning_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.execution_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.time.execution",
                value=query.execution_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.elapsed_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.time.elapsed",
                value=query.elapsed_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        # Resource metrics
        if query.cpu_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.cpu_time",
                value=query.cpu_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.peak_memory_bytes is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.memory.peak",
                value=query.peak_memory_bytes,
                unit="bytes",
                labels=labels,
            ))
        
        # Data processing metrics
        if query.input_rows is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.data.input.rows",
                value=query.input_rows,
                unit="count",
                labels=labels,
            ))
        
        if query.input_bytes is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.data.input.bytes",
                value=query.input_bytes,
                unit="bytes",
                labels=labels,
            ))
        
        if query.output_rows is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.data.output.rows",
                value=query.output_rows,
                unit="count",
                labels=labels,
            ))
        
        if query.output_bytes is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                metric_type=MetricType.QUERY_EXECUTION,
                name="trino.query.data.output.bytes",
                value=query.output_bytes,
                unit="bytes",
                labels=labels,
            ))
        
        return metrics
