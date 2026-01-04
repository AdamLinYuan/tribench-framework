"""
Monitoring metrics storage operations.

Handles storage and retrieval of system and monitoring metrics.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy import func

from ..connection import get_db_session
from ..models import SystemMetric, MonitoringMetric
from tribench.defaults import Defaults

logger = logging.getLogger(__name__)


class MetricStore:
    """Service for monitoring and system metrics database operations."""
    
    def add_system_metrics(
        self,
        run_id: int,
        cpu_percent_mean: Optional[float] = None,
        cpu_percent_max: Optional[float] = None,
        memory_percent_mean: Optional[float] = None,
        memory_percent_max: Optional[float] = None,
        memory_bytes_mean: Optional[int] = None,
        memory_bytes_max: Optional[int] = None,
        disk_read_bytes: Optional[int] = None,
        disk_write_bytes: Optional[int] = None,
        network_sent_bytes: Optional[int] = None,
        network_recv_bytes: Optional[int] = None,
        collection_interval_seconds: Optional[float] = None,
        total_samples: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Add aggregated system metrics for a run.
        
        Args:
            run_id: Run ID
            cpu_percent_mean: Mean CPU utilization (%)
            cpu_percent_max: Max CPU utilization (%)
            memory_percent_mean: Mean memory utilization (%)
            memory_percent_max: Max memory utilization (%)
            memory_bytes_mean: Mean memory usage (bytes)
            memory_bytes_max: Max memory usage (bytes)
            disk_read_bytes: Total disk read (bytes)
            disk_write_bytes: Total disk write (bytes)
            network_sent_bytes: Total network sent (bytes)
            network_recv_bytes: Total network received (bytes)
            collection_interval_seconds: Monitoring interval
            total_samples: Number of monitoring samples
            **kwargs: Additional metrics
        """
        with get_db_session() as session:
            # Check if metrics already exist
            existing = session.query(SystemMetric).filter_by(run_id=run_id).first()
            if existing:
                # Update existing metrics
                for key, value in kwargs.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new metrics
                metrics = SystemMetric(
                    run_id=run_id,
                    cpu_percent_mean=cpu_percent_mean,
                    cpu_percent_max=cpu_percent_max,
                    memory_percent_mean=memory_percent_mean,
                    memory_percent_max=memory_percent_max,
                    memory_bytes_mean=memory_bytes_mean,
                    memory_bytes_max=memory_bytes_max,
                    disk_read_bytes=disk_read_bytes,
                    disk_write_bytes=disk_write_bytes,
                    network_sent_bytes=network_sent_bytes,
                    network_recv_bytes=network_recv_bytes,
                    collection_interval_seconds=collection_interval_seconds,
                    total_samples=total_samples,
                )
                
                # Add additional metrics
                for key, value in kwargs.items():
                    if hasattr(metrics, key):
                        setattr(metrics, key, value)
                
                session.add(metrics)
            
            session.commit()
            logger.debug(f"Added system metrics for run {run_id}")
    
    def save_monitoring_metrics(
        self,
        run_id: int,
        metrics: List[Any],  # List of Metric objects from monitoring.base
        batch_size: int = Defaults.Retry.STORAGE_BATCH_SIZE
    ) -> int:
        """
        Save monitoring metrics to the database.
        
        Args:
            run_id: Run ID to associate metrics with
            metrics: List of Metric objects from monitoring system
            batch_size: Number of metrics to insert per batch
            
        Returns:
            Number of metrics saved
        """
        if not metrics:
            logger.debug(f"No metrics to save for run {run_id}")
            return 0
        
        total_saved = 0
        
        try:
            with get_db_session() as session:
                # Process metrics in batches to avoid memory issues
                for i in range(0, len(metrics), batch_size):
                    batch = metrics[i:i + batch_size]
                    
                    for metric in batch:
                        monitoring_metric = MonitoringMetric(
                            run_id=run_id,
                            timestamp=metric.timestamp,
                            metric_type=metric.metric_type.value,  # Convert enum to string
                            metric_name=metric.name,
                            value=float(metric.value) if isinstance(metric.value, (int, float)) else None,
                            value_text=str(metric.value) if not isinstance(metric.value, (int, float)) else None,
                            unit=metric.unit,
                            labels=metric.labels,
                        )
                        session.add(monitoring_metric)
                    
                    session.commit()
                    total_saved += len(batch)
                    logger.debug(f"Saved batch of {len(batch)} metrics (total: {total_saved}/{len(metrics)})")
            
            logger.info(f"Saved {total_saved} monitoring metrics for run {run_id}")
            return total_saved
            
        except Exception as e:
            logger.error(f"Failed to save monitoring metrics: {e}", exc_info=True)
            raise
    
    def get_monitoring_metrics(
        self,
        run_id: int,
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve monitoring metrics from the database.
        
        Args:
            run_id: Run ID
            metric_type: Filter by metric type (optional)
            metric_name: Filter by metric name (optional)
            start_time: Filter by start timestamp (optional)
            end_time: Filter by end timestamp (optional)
            limit: Maximum number of metrics to return (optional)
            
        Returns:
            List of monitoring metrics as dictionaries
        """
        with get_db_session() as session:
            query = session.query(MonitoringMetric).filter(MonitoringMetric.run_id == run_id)
            
            if metric_type:
                query = query.filter(MonitoringMetric.metric_type == metric_type)
            if metric_name:
                query = query.filter(MonitoringMetric.metric_name == metric_name)
            if start_time:
                query = query.filter(MonitoringMetric.timestamp >= start_time)
            if end_time:
                query = query.filter(MonitoringMetric.timestamp <= end_time)
            
            query = query.order_by(MonitoringMetric.timestamp)
            
            if limit:
                query = query.limit(limit)
            
            metrics = query.all()
            
            result = []
            for m in metrics:
                result.append({
                    'id': m.id,
                    'run_id': m.run_id,
                    'timestamp': m.timestamp.isoformat(),
                    'metric_type': m.metric_type,
                    'metric_name': m.metric_name,
                    'value': m.value,
                    'value_text': m.value_text,
                    'unit': m.unit,
                    'labels': m.labels,
                })
            
            return result
    
    def get_monitoring_metrics_summary(
        self,
        run_id: int,
        metric_name: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Get summary statistics for monitoring metrics.
        
        Args:
            run_id: Run ID
            metric_name: Filter by metric name (optional)
            
        Returns:
            Dictionary mapping metric names to summary statistics
        """
        with get_db_session() as session:
            query = session.query(
                MonitoringMetric.metric_name,
                func.count(MonitoringMetric.id).label('count'),
                func.min(MonitoringMetric.value).label('min'),
                func.max(MonitoringMetric.value).label('max'),
                func.avg(MonitoringMetric.value).label('mean'),
            ).filter(
                MonitoringMetric.run_id == run_id,
                MonitoringMetric.value.isnot(None)  # Only numeric values
            ).group_by(MonitoringMetric.metric_name)
            
            if metric_name:
                query = query.filter(MonitoringMetric.metric_name == metric_name)
            
            results = query.all()
            
            summary = {}
            for row in results:
                summary[row.metric_name] = {
                    'count': row.count,
                    'min': float(row.min) if row.min is not None else None,
                    'max': float(row.max) if row.max is not None else None,
                    'mean': float(row.mean) if row.mean is not None else None,
                }
            
            return summary
