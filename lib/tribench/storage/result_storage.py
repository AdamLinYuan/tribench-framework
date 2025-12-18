"""
High-level API for storing and retrieving experiment results.

Provides a convenient interface for experiment execution code to store
results in the database without dealing with SQLAlchemy directly.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .connection import get_db_session
from .models import (
    Experiment,
    ExperimentRun,
    QueryExecution,
    SystemMetric,
    MonitoringMetric,
)
from tribench.defaults import Defaults

logger = logging.getLogger(__name__)


class ResultStorage:
    """
    Service for storing and retrieving experiment results.
    
    Provides high-level methods that hide SQLAlchemy complexity from
    experiment execution code.
    """
    
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
        with get_db_session() as session:
            # Check if experiment already exists
            experiment = session.query(Experiment).filter_by(name=name).first()
            
            if experiment:
                # Update configuration if changed
                experiment.config = config
                experiment.description = description or experiment.description
                experiment.dataset_name = dataset_name or experiment.dataset_name
                experiment.system_name = system_name or experiment.system_name
                experiment.tags = tags or experiment.tags
                experiment.updated_at = datetime.now()
                session.commit()
                logger.info(f"Updated existing experiment: {name} (ID: {experiment.id})")
            else:
                # Create new experiment
                experiment = Experiment(
                    name=name,
                    experiment_type=experiment_type,
                    config=config,
                    description=description,
                    dataset_name=dataset_name,
                    system_name=system_name,
                    tags=tags,
                )
                session.add(experiment)
                session.commit()
                logger.info(f"Created new experiment: {name} (ID: {experiment.id})")
            
            return experiment.id
    
    def create_run(
        self,
        experiment_id: int,
        run_number: Optional[int] = None,
        run_type: str = "measured",
        start_time: Optional[datetime] = None,
        monitoring_enabled: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Create a new experiment run.
        
        Args:
            experiment_id: ID of the experiment
            run_number: Run number (1, 2, 3, ...). If None, auto-calculates next number.
            run_type: "warmup" or "measured"
            start_time: Run start time (defaults to now)
            monitoring_enabled: Whether monitoring is enabled
            metadata: Optional metadata
            
        Returns:
            Run ID
        """
        with get_db_session() as session:
            # Auto-calculate run number if not provided
            if run_number is None:
                max_run = session.query(ExperimentRun).filter_by(
                    experiment_id=experiment_id
                ).order_by(ExperimentRun.run_number.desc()).first()
                run_number = (max_run.run_number + 1) if max_run else 1
            
            run = ExperimentRun(
                experiment_id=experiment_id,
                run_number=run_number,
                run_type=run_type,
                start_time=start_time or datetime.now(),
                status="running",
                monitoring_enabled=monitoring_enabled,
                metadata=metadata,
            )
            session.add(run)
            session.commit()
            logger.debug(f"Created run {run_number} for experiment {experiment_id} (ID: {run.id})")
            return run.id
    
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
        """
        Mark a run as completed and update statistics.
        
        Args:
            run_id: Run ID
            status: Final status ("completed", "failed", "timeout")
            end_time: End time (defaults to now)
            validation_passed: Whether validation passed
            validation_errors: List of validation errors
            error_message: Error message if failed
            error_traceback: Error traceback if failed
            monitoring_file: Path to monitoring data file
        """
        with get_db_session() as session:
            run = session.query(ExperimentRun).filter_by(id=run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")
            
            run.end_time = end_time or datetime.now()
            run.duration_seconds = (run.end_time - run.start_time).total_seconds()
            run.status = status
            run.validation_passed = validation_passed
            run.validation_errors = validation_errors
            run.error_message = error_message
            run.error_traceback = error_traceback
            run.monitoring_file = monitoring_file
            
            # Calculate query statistics
            query_count = session.query(QueryExecution).filter_by(run_id=run_id).count()
            succeeded = session.query(QueryExecution).filter_by(run_id=run_id, status="completed").count()
            failed = session.query(QueryExecution).filter_by(run_id=run_id, status="failed").count()
            
            run.queries_total = query_count
            run.queries_succeeded = succeeded
            run.queries_failed = failed
            
            # Sum execution times
            from sqlalchemy import func
            total_time = session.query(func.sum(QueryExecution.execution_time)).filter_by(run_id=run_id).scalar()
            run.total_execution_time = float(total_time) if total_time else None
            
            session.commit()
            logger.info(f"Completed run {run_id}: {status}, {query_count} queries, {run.duration_seconds:.2f}s")
    
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
        """
        Add a query execution record.
        
        Args:
            run_id: Run ID
            query_name: Query name/identifier
            start_time: Query start time
            end_time: Query end time
            status: Query status ("completed", "failed", "timeout")
            query_number: Query number (for TPC-H/TPC-DS)
            query_text: Actual SQL query
            query_id: Trino query ID
            execution_time: Execution time in seconds
            rows_returned: Number of rows returned
            result_checksum: Result checksum for validation
            validation_passed: Whether validation passed
            expected_row_count: Expected row count
            expected_checksum: Expected checksum
            error_message: Error message if failed
            error_code: Error code if failed
            metadata: Additional metadata
            **metrics: Additional Trino metrics (planning_time_ms, cpu_time_ms, etc.)
            
        Returns:
            Query execution ID
        """
        with get_db_session() as session:
            query_exec = QueryExecution(
                run_id=run_id,
                query_name=query_name,
                query_number=query_number,
                query_text=query_text,
                start_time=start_time,
                end_time=end_time,
                execution_time=execution_time,
                status=status,
                query_id=query_id,
                rows_returned=rows_returned,
                result_checksum=result_checksum,
                validation_passed=validation_passed,
                expected_row_count=expected_row_count,
                expected_checksum=expected_checksum,
                error_message=error_message,
                error_code=error_code,
                metadata=metadata,
            )
            
            # Add Trino-specific metrics
            for key, value in metrics.items():
                if hasattr(query_exec, key) and value is not None:
                    setattr(query_exec, key, value)
            
            session.add(query_exec)
            session.commit()
            logger.debug(f"Added query execution: {query_name} (ID: {query_exec.id})")
            return query_exec.id
    
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
    
    def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get experiment by name."""
        with get_db_session() as session:
            experiment = session.query(Experiment).filter_by(name=name).first()
            if not experiment:
                return None
            
            return {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "experiment_type": experiment.experiment_type,
                "dataset_name": experiment.dataset_name,
                "system_name": experiment.system_name,
                "config": experiment.config,
                "tags": experiment.tags,
                "created_at": experiment.created_at,
                "updated_at": experiment.updated_at,
            }
    
    def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get run details by ID."""
        with get_db_session() as session:
            run = session.query(ExperimentRun).filter_by(id=run_id).first()
            if not run:
                return None
            
            return {
                "id": run.id,
                "experiment_id": run.experiment_id,
                "run_number": run.run_number,
                "run_type": run.run_type,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "duration_seconds": run.duration_seconds,
                "status": run.status,
                "queries_total": run.queries_total,
                "queries_succeeded": run.queries_succeeded,
                "queries_failed": run.queries_failed,
                "total_execution_time": run.total_execution_time,
                "validation_passed": run.validation_passed,
                "validation_errors": run.validation_errors,
                "monitoring_enabled": run.monitoring_enabled,
                "monitoring_file": run.monitoring_file,
                "metadata": run.metadata,
            }
    
    def list_experiments(
        self,
        experiment_type: Optional[str] = None,
        dataset_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List experiments with optional filtering.
        
        Args:
            experiment_type: Filter by experiment type
            dataset_name: Filter by dataset name
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of experiment dictionaries
        """
        with get_db_session() as session:
            query = session.query(Experiment)
            
            if experiment_type:
                query = query.filter_by(experiment_type=experiment_type)
            if dataset_name:
                query = query.filter_by(dataset_name=dataset_name)
            
            experiments = query.order_by(Experiment.created_at.desc()).limit(limit).offset(offset).all()
            
            return [
                {
                    "id": exp.id,
                    "name": exp.name,
                    "description": exp.description,
                    "experiment_type": exp.experiment_type,
                    "dataset_name": exp.dataset_name,
                    "system_name": exp.system_name,
                    "tags": exp.tags,
                    "created_at": exp.created_at,
                    "updated_at": exp.updated_at,
                    "run_count": len(exp.runs),
                }
                for exp in experiments
            ]
    
    def get_experiment_runs(
        self,
        experiment_id: int,
        run_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all runs for an experiment.
        
        Args:
            experiment_id: Experiment ID
            run_type: Filter by run type ("warmup" or "measured")
            status: Filter by status
            
        Returns:
            List of run dictionaries
        """
        with get_db_session() as session:
            query = session.query(ExperimentRun).filter_by(experiment_id=experiment_id)
            
            if run_type:
                query = query.filter_by(run_type=run_type)
            if status:
                query = query.filter_by(status=status)
            
            runs = query.order_by(ExperimentRun.start_time.desc()).all()
            
            return [
                {
                    "id": run.id,
                    "run_number": run.run_number,
                    "run_type": run.run_type,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "duration_seconds": run.duration_seconds,
                    "status": run.status,
                    "queries_total": run.queries_total,
                    "queries_succeeded": run.queries_succeeded,
                    "queries_failed": run.queries_failed,
                    "validation_passed": run.validation_passed,
                }
                for run in runs
            ]
    
    def get_run_query_executions(self, run_id: int) -> List[Dict[str, Any]]:
        """
        Get all query executions for a specific run.
        
        Args:
            run_id: Run ID
            
        Returns:
            List of query execution dictionaries
        """
        with get_db_session() as session:
            query_executions = (
                session.query(QueryExecution)
                .filter(QueryExecution.run_id == run_id)
                .order_by(QueryExecution.start_time)
                .all()
            )
            
            # Convert ORM objects to dictionaries
            return [
                {
                    "id": qe.id,
                    "run_id": qe.run_id,
                    "query_name": qe.query_name,
                    "query_number": qe.query_number,
                    "query_text": qe.query_text,
                    "start_time": qe.start_time,
                    "end_time": qe.end_time,
                    "execution_time": qe.execution_time,
                    "status": qe.status,
                    # Trino-specific metrics
                    "query_id": qe.query_id,
                    "planning_time_ms": qe.planning_time_ms,
                    "analysis_time_ms": qe.analysis_time_ms,
                    "execution_time_ms": qe.execution_time_ms,
                    "cpu_time_ms": qe.cpu_time_ms,
                    "scheduled_time_ms": qe.scheduled_time_ms,
                    "blocked_time_ms": qe.blocked_time_ms,
                    # Data processing metrics
                    "input_rows": qe.input_rows,
                    "input_bytes": qe.input_bytes,
                    "output_rows": qe.output_rows,
                    "output_bytes": qe.output_bytes,
                    "physical_input_bytes": qe.physical_input_bytes,
                    "peak_memory_bytes": qe.peak_memory_bytes,
                    # Results
                    "rows_returned": qe.rows_returned,
                    "result_checksum": qe.result_checksum,
                    # Validation
                    "validation_passed": qe.validation_passed,
                    "expected_row_count": qe.expected_row_count,
                    "expected_checksum": qe.expected_checksum,
                    # Error information
                    "error_message": qe.error_message,
                    "error_code": qe.error_code,
                    "error_traceback": qe.error_traceback,
                    # Metadata
                    "query_metadata": qe.query_metadata,
                }
                for qe in query_executions
            ]
    
    def get_experiment_by_id(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get experiment by ID.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment dictionary or None if not found
        """
        with get_db_session() as session:
            experiment = session.query(Experiment).filter(Experiment.id == experiment_id).first()
            if not experiment:
                return None
            
            return {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "experiment_type": experiment.experiment_type,
                "dataset_name": experiment.dataset_name,
                "system_name": experiment.system_name,
                "config": experiment.config,
                "tags": experiment.tags,
                "created_at": experiment.created_at,
                "updated_at": experiment.updated_at,
            }
    
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
        from sqlalchemy import func
        
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

