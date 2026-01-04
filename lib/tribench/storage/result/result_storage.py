"""
Unified result storage interface.

Provides a single API that delegates to specialized storage modules.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from .experiment_store import ExperimentStore
from .run_store import RunStore
from .query_store import QueryStore
from .metric_store import MetricStore

logger = logging.getLogger(__name__)


class ResultStorage:
    """
    Unified service for storing and retrieving experiment results.
    
    Delegates to specialized stores while providing high-level methods that hide
    SQLAlchemy complexity from experiment execution code.
    """
    
    def __init__(self):
        """Initialize storage delegates."""
        self._experiment_store = ExperimentStore()
        self._run_store = RunStore()
        self._query_store = QueryStore()
        self._metric_store = MetricStore()
    
    # ===== Experiment Operations =====
    
    def create_or_get_experiment(
        self,
        name: str,
        experiment_type: str,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        dataset_name: Optional[str] = None,
        system_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """
        Create a new experiment or get existing one by name.
        
        Args:
            name: Experiment name (unique identifier)
            experiment_type: Type of experiment (e.g., "trino")
            config: Full experiment configuration
            description: Optional description
            dataset_name: Dataset used (e.g., "tpch-sf1")
            system_name: System name (e.g., "trino")
            tags: Optional tags for categorization
            
        Returns:
            Experiment ID
        """
        return self._experiment_store.create_or_get_experiment(
            name=name,
            experiment_type=experiment_type,
            config=config,
            description=description,
            dataset_name=dataset_name,
            system_name=system_name,
            tags=tags,
        )
    
    def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get experiment by name."""
        return self._experiment_store.get_experiment_by_name(name)
    
    def get_experiment_by_id(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """Get experiment by ID."""
        return self._experiment_store.get_experiment_by_id(experiment_id)
    
    def list_experiments(
        self,
        experiment_type: Optional[str] = None,
        dataset_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filtering."""
        return self._experiment_store.list_experiments(
            experiment_type=experiment_type,
            dataset_name=dataset_name,
            limit=limit,
            offset=offset,
        )
    
    # ===== Run Operations =====
    
    def create_run(
        self,
        experiment_id: int,
        run_number: Optional[int] = None,
        run_type: str = "measured",
        start_time: Optional[datetime] = None,
        monitoring_enabled: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new experiment run."""
        return self._run_store.create_run(
            experiment_id=experiment_id,
            run_number=run_number,
            run_type=run_type,
            start_time=start_time,
            monitoring_enabled=monitoring_enabled,
            metadata=metadata,
        )
    
    def complete_run(
        self,
        run_id: int,
        status: str = "completed",
        end_time: Optional[datetime] = None,
        validation_passed: Optional[bool] = None,
        validation_errors: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        error_traceback: Optional[str] = None,
        monitoring_file: Optional[str] = None,
    ) -> None:
        """Mark a run as completed and update statistics."""
        self._run_store.complete_run(
            run_id=run_id,
            status=status,
            end_time=end_time,
            validation_passed=validation_passed,
            validation_errors=validation_errors,
            error_message=error_message,
            error_traceback=error_traceback,
            monitoring_file=monitoring_file,
        )
    
    def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get run details by ID."""
        return self._run_store.get_run(run_id)
    
    def get_experiment_runs(
        self,
        experiment_id: int,
        run_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all runs for an experiment."""
        return self._run_store.get_experiment_runs(
            experiment_id=experiment_id,
            run_type=run_type,
            status=status,
        )
    
    # ===== Query Operations =====
    
    def add_query_execution(
        self,
        run_id: int,
        query_name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        status: str = "completed",
        query_number: Optional[int] = None,
        query_text: Optional[str] = None,
        query_id: Optional[str] = None,
        execution_time: Optional[float] = None,
        rows_returned: Optional[int] = None,
        result_checksum: Optional[str] = None,
        validation_passed: Optional[bool] = None,
        expected_row_count: Optional[int] = None,
        expected_checksum: Optional[str] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **metrics: Any,
    ) -> int:
        """Add a query execution record."""
        return self._query_store.add_query_execution(
            run_id=run_id,
            query_name=query_name,
            start_time=start_time,
            end_time=end_time,
            status=status,
            query_number=query_number,
            query_text=query_text,
            query_id=query_id,
            execution_time=execution_time,
            rows_returned=rows_returned,
            result_checksum=result_checksum,
            validation_passed=validation_passed,
            expected_row_count=expected_row_count,
            expected_checksum=expected_checksum,
            error_message=error_message,
            error_code=error_code,
            metadata=metadata,
            **metrics,
        )
    
    def get_run_query_executions(self, run_id: int) -> List[Dict[str, Any]]:
        """Get all query executions for a specific run."""
        return self._query_store.get_run_query_executions(run_id)
    
    # ===== Metrics Operations =====
    
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
        """Add aggregated system metrics for a run."""
        self._metric_store.add_system_metrics(
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
            **kwargs,
        )
    
    def save_monitoring_metrics(
        self,
        run_id: int,
        metrics: List[Any],
        batch_size: int = 1000
    ) -> int:
        """Save monitoring metrics to the database."""
        return self._metric_store.save_monitoring_metrics(
            run_id=run_id,
            metrics=metrics,
            batch_size=batch_size,
        )
    
    def get_monitoring_metrics(
        self,
        run_id: int,
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve monitoring metrics from the database."""
        return self._metric_store.get_monitoring_metrics(
            run_id=run_id,
            metric_type=metric_type,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
    
    def get_monitoring_metrics_summary(
        self,
        run_id: int,
        metric_name: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for monitoring metrics."""
        return self._metric_store.get_monitoring_metrics_summary(
            run_id=run_id,
            metric_name=metric_name,
        )
