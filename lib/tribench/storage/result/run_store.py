"""
Run storage operations.

Handles CRUD operations for ExperimentRun entities and lifecycle management.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy import func

from ..connection import get_db_session
from ..models import ExperimentRun, QueryExecution

logger = logging.getLogger(__name__)


class RunStore:
    """Service for experiment run database operations."""
    
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
            total_time = session.query(func.sum(QueryExecution.execution_time)).filter_by(run_id=run_id).scalar()
            run.total_execution_time = float(total_time) if total_time else None
            
            session.commit()
            logger.info(f"Completed run {run_id}: {status}, {query_count} queries, {run.duration_seconds:.2f}s")
    
    def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get run details by ID."""
        with get_db_session() as session:
            run = session.query(ExperimentRun).filter_by(id=run_id).first()
            if not run:
                return None
            
            return self._run_to_dict(run)
    
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
    
    @staticmethod
    def _run_to_dict(run: ExperimentRun) -> Dict[str, Any]:
        """Convert ExperimentRun ORM object to dictionary."""
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
