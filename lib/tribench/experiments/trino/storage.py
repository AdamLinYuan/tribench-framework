"""Storage integration for Trino experiments.

Handles database and JSON file storage for experiment results.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...storage import ResultStorage
    from ..result_collector import ResultCollector
    from ...core.result import Result

logger = logging.getLogger(__name__)

# Database storage imports
try:
    from ...storage import ResultStorage, init_database
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False


class ExperimentStorageMixin:
    """
    Mixin class providing storage capabilities for experiments.
    
    This mixin handles:
    - Database initialization and experiment/run record creation
    - Query execution recording
    - JSON file storage
    
    Attributes expected from the host class:
    - config: ExperimentConfig
    - enable_database: bool
    - enable_json: bool
    - result_storage: Optional[ResultStorage]
    - result_collector: ResultCollector
    - experiment_id: Optional[int]
    - current_run_id: Optional[int]
    - run_results: List[Result]
    - total_queries_executed: int
    """
    
    def _init_database_storage(self, enable_database: bool) -> None:
        """
        Initialize database storage if enabled.
        
        Args:
            enable_database: Whether database storage is requested
        """
        self.enable_database = enable_database and STORAGE_AVAILABLE
        self.result_storage: Optional['ResultStorage'] = None
        self.experiment_id: Optional[int] = None
        self.current_run_id: Optional[int] = None
        
        if self.enable_database:
            try:
                init_database()
                self.result_storage = ResultStorage()
                logger.info("Database storage initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database storage: {e}")
                self.enable_database = False
        else:
            if enable_database and not STORAGE_AVAILABLE:
                logger.warning("Database storage requested but not available")
    
    def _create_experiment_record(self) -> Optional[int]:
        """
        Create or get experiment record in database.
        
        Returns:
            Experiment ID if successful, None otherwise
        """
        if not self.enable_database or not self.result_storage:
            return None
            
        try:
            # Extract tags from metadata if available
            tags = self.config.metadata.get('tags', []) if self.config.metadata else []
            
            # Get dataset name - check multiple sources in order of preference
            dataset_name = self._resolve_dataset_name()
            
            experiment_id = self.result_storage.create_or_get_experiment(
                name=self.config.name,
                experiment_type="trino_query",
                config=self.config.to_dict(),
                dataset_name=dataset_name,
                tags=tags,
            )
            logger.info(f"Database: Experiment record created/retrieved (ID: {experiment_id})")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to create experiment record in database: {e}")
            self.enable_database = False
            return None
    
    def _resolve_dataset_name(self) -> Optional[str]:
        """Resolve dataset name from various configuration sources."""
        dataset_name = self.config.dataset
        
        if not dataset_name and self.config.metadata:
            # Try metadata.dataset first
            dataset_name = self.config.metadata.get('dataset')
            
            # If not found, try to construct from scale_factor and benchmark
            if not dataset_name:
                benchmark = self.config.metadata.get('benchmark', '').lower()
                scale_factor = self.config.metadata.get('scale_factor')
                if benchmark and scale_factor:
                    dataset_name = f"{benchmark}-{scale_factor}"
        
        # Fall back to catalog.schema if still no dataset name
        if not dataset_name and self.config.connection:
            catalog = self.config.connection.get('catalog')
            schema = self.config.connection.get('schema')
            if catalog and schema:
                dataset_name = f"{catalog}.{schema}"
        
        return dataset_name
    
    def _create_run_record(self, experiment_id: int) -> Optional[int]:
        """
        Create a run record in the database.
        
        Args:
            experiment_id: Parent experiment ID
            
        Returns:
            Run ID if successful, None otherwise
        """
        if not self.enable_database or not self.result_storage:
            return None
            
        try:
            run_id = self.result_storage.create_run(
                experiment_id=experiment_id,
                run_type="measured",
            )
            logger.info(f"Database: Run record created (ID: {run_id})")
            return run_id
        except Exception as e:
            logger.error(f"Failed to create run record in database: {e}")
            return None
    
    def _complete_run_record(self, run_id: int, status: str = "completed") -> None:
        """
        Mark a run record as completed in the database.
        
        Args:
            run_id: Run ID to complete
            status: Final status
        """
        if not self.enable_database or not self.result_storage:
            return
            
        try:
            self.result_storage.complete_run(
                run_id=run_id,
                status=status,
            )
            logger.info(f"Database: Run completed (ID: {run_id})")
        except Exception as e:
            logger.error(f"Failed to complete run record in database: {e}")
    
    def _save_query_execution(
        self,
        run_id: int,
        query_name: str,
        query_sql: str,
        duration: float,
        status: str,
        error: Optional[Exception] = None,
        query_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Save a query execution to the database.
        
        Args:
            run_id: Parent run ID
            query_name: Name of the query
            query_sql: SQL text
            duration: Execution duration in seconds
            status: Execution status ('success' or 'failed')
            error: Exception if failed
            query_metadata: Additional metadata from executor
        """
        if not self.enable_database or not self.result_storage:
            return
            
        try:
            query_end_time = datetime.now()
            query_start_time = query_end_time - timedelta(seconds=duration)
            
            # Extract Trino-specific metrics from metadata
            metrics = {}
            if query_metadata:
                # HIGH PRIORITY: Planning and analysis time breakdown
                if "planning_time_ms" in query_metadata:
                    metrics["planning_time_ms"] = query_metadata["planning_time_ms"]
                if "analysis_time_ms" in query_metadata:
                    metrics["analysis_time_ms"] = query_metadata["analysis_time_ms"]
                if "execution_time_ms" in query_metadata:
                    metrics["execution_time_ms"] = query_metadata["execution_time_ms"]
                
                # Existing timing metrics
                if "cpu_time_ms" in query_metadata:
                    metrics["cpu_time_ms"] = query_metadata["cpu_time_ms"]
                if "scheduled_time_ms" in query_metadata:
                    metrics["scheduled_time_ms"] = query_metadata["scheduled_time_ms"]
                if "blocked_time_ms" in query_metadata:
                    metrics["blocked_time_ms"] = query_metadata["blocked_time_ms"]
                
                # Data processing metrics
                if "processed_rows" in query_metadata:
                    metrics["input_rows"] = query_metadata["processed_rows"]
                if "processed_bytes" in query_metadata:
                    metrics["input_bytes"] = query_metadata["processed_bytes"]
                if "peak_memory_bytes" in query_metadata:
                    metrics["peak_memory_bytes"] = query_metadata["peak_memory_bytes"]
                
                # HIGH PRIORITY: Spill metrics for memory pressure analysis
                if "spilled_bytes" in query_metadata:
                    metrics["spilled_bytes"] = query_metadata["spilled_bytes"]
                
                # MEDIUM PRIORITY: Parallelism metrics
                if "total_splits" in query_metadata:
                    metrics["total_splits"] = query_metadata["total_splits"]
                if "completed_splits" in query_metadata:
                    metrics["completed_splits"] = query_metadata["completed_splits"]
                if "total_tasks" in query_metadata:
                    metrics["total_tasks"] = query_metadata["total_tasks"]
                
                # MEDIUM PRIORITY: Query plan hash for plan regression detection
                if "query_plan_hash" in query_metadata:
                    metrics["query_plan_hash"] = query_metadata["query_plan_hash"]
            
            self.result_storage.add_query_execution(
                run_id=run_id,
                query_name=query_name,
                query_text=query_sql,
                start_time=query_start_time,
                end_time=query_end_time,
                execution_time=duration,
                status="completed" if status == "success" else "failed",
                error_message=str(error) if error else None,
                query_id=query_metadata.get("query_id") if query_metadata else None,
                metadata=query_metadata if query_metadata else None,
                **metrics,  # Pass all extracted metrics as keyword arguments
            )
        except Exception as e:
            logger.error(f"Failed to save query execution to database: {e}")
    
    def _save_query_to_json(
        self,
        query_name: str,
        query_source: str,
        run_number: int,
        duration: float,
        status: str,
        error: Optional[Exception] = None,
        query_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional['Result']:
        """
        Save a query execution result to JSON file.
        
        Args:
            query_name: Name of the query
            query_source: Source of the query (inline/file path)
            run_number: Run number (1-indexed)
            duration: Execution duration in seconds
            status: Execution status ('success' or 'failed')
            error: Exception if failed
            query_metadata: Additional metadata from executor
            
        Returns:
            Result object if created, None otherwise
        """
        if not getattr(self, 'enable_json', False):
            return None
            
        result = self.result_collector.create_result(
            experiment_name=self.config.name,
            experiment_type="trino_query",
            duration_seconds=duration,
            status=status,
            query_metadata=query_metadata,
            error=error,
            metadata={
                "query_name": query_name,
                "run_number": run_number,
                "query_source": query_source,
            }
        )
        
        # Store result
        self.run_results.append(result)
        
        # Save individual result as JSON file
        self.result_collector.save_result(result)
        
        return result
    
    def _build_results_dict(
        self,
        duration: Optional[float],
        queries_count: int,
        monitoring_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build the final results dictionary.
        
        Args:
            duration: Total experiment duration
            queries_count: Number of queries executed per run
            monitoring_file: Path to monitoring file if saved
            
        Returns:
            Results dictionary
        """
        # Aggregate results
        aggregated = self.result_collector.aggregate_results(self.run_results)
        
        # Calculate runs completed
        runs_completed = len(self.run_results) if self.run_results else self.total_queries_executed
        
        results = {
            "experiment_name": self.config.name,
            "total_duration_seconds": duration,
            "runs_completed": runs_completed,
            "runs_requested": self.config.runs * queries_count,
            "statistics": aggregated,
            "results": [r.to_dict() for r in self.run_results],
        }
        
        # Add monitoring summary if available
        if monitoring_file:
            results["monitoring"] = {
                "enabled": True,
                "metrics_file": str(monitoring_file),
                "summary": self._get_monitoring_summary() if hasattr(self, '_get_monitoring_summary') else {},
            }
        else:
            results["monitoring"] = {"enabled": False}
        
        # Add database reference if available
        if self.enable_database and self.experiment_id:
            results["database"] = {
                "enabled": True,
                "experiment_id": self.experiment_id,
            }
        else:
            results["database"] = {"enabled": False}
        
        return results


def is_storage_available() -> bool:
    """Check if database storage module is available."""
    return STORAGE_AVAILABLE
