"""
Query execution storage operations.

Handles CRUD operations for QueryExecution entities.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..connection import get_db_session
from ..models import QueryExecution

logger = logging.getLogger(__name__)


class QueryStore:
    """Service for query execution database operations."""
    
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
                    # HIGH PRIORITY: Spill metrics for memory pressure analysis
                    "spilled_bytes": qe.spilled_bytes,
                    # MEDIUM PRIORITY: Parallelism metrics
                    "total_splits": qe.total_splits,
                    "completed_splits": qe.completed_splits,
                    "total_tasks": qe.total_tasks,
                    # MEDIUM PRIORITY: Query plan hash for plan regression detection
                    "query_plan_hash": qe.query_plan_hash,
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
