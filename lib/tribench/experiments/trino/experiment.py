"""Core Trino experiment implementation.

Main TrinoExperiment class that orchestrates query execution against Trino.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ...core.experiment import Experiment, ExperimentConfig
from ...core.result import Result
from ...config import ConnectionConfig, ConnectionPool
from ...defaults import Defaults
from ..query_executor import QueryExecutor, QueryExecutionError
from ..result_collector import ResultCollector

from .monitoring import ExperimentMonitoringMixin, is_monitoring_available
from .storage import ExperimentStorageMixin, is_storage_available
from .parallel import ParallelExecutionMixin
from .queries import collect_queries, validate_results

logger = logging.getLogger(__name__)


class TrinoExperiment(
    ExperimentMonitoringMixin,
    ExperimentStorageMixin,
    ParallelExecutionMixin,
    Experiment
):
    """
    Concrete implementation of Experiment for Trino SQL workloads.
    
    Executes SQL queries against Trino, collects metrics, and validates results.
    Uses mixins for modular functionality:
    - ExperimentMonitoringMixin: Monitoring session management
    - ExperimentStorageMixin: Database and JSON storage
    - ParallelExecutionMixin: Parallel query execution
    """
    
    def __init__(self, 
                 config: ExperimentConfig,
                 results_dir: Optional[Path] = None,
                 enable_monitoring: bool = True,
                 enable_database: bool = True,
                 enable_json: bool = False):
        """
        Initialize a TrinoExperiment.
        
        Args:
            config: Experiment configuration
            results_dir: Directory to store results (optional)
            enable_monitoring: Enable resource and query monitoring (default: True)
            enable_database: Enable database storage for results (default: True)
            enable_json: Enable JSON file storage for results (default: False)
        """
        super().__init__(config)
        
        # Initialize executor with connection parameters
        connection_config = ConnectionConfig.from_dict(config.connection or {})
        self.executor = QueryExecutor(
            connection=connection_config,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        
        # Store connection config for monitoring and parallel execution
        self.connection_config = connection_config
        
        # Connection pool for parallel query execution (lazy initialization)
        self._connection_pool: Optional[ConnectionPool] = None
        
        # Storage configuration
        self.enable_json = enable_json
        
        # Initialize result collector (for JSON file storage when enabled)
        self.result_collector = ResultCollector(results_dir)
        
        # Storage for individual run results
        self.run_results: List[Result] = []
        
        # Track query execution counts
        self.total_queries_executed = 0
        
        # Initialize database storage (from mixin)
        self._init_database_storage(enable_database)
        
        # Initialize monitoring session (from mixin)
        self.monitoring_session = None
        self.trino_monitor = None
        self.enable_monitoring = enable_monitoring and is_monitoring_available()
        
        if self.enable_monitoring:
            self._setup_monitoring(connection_config)
        elif enable_monitoring and not is_monitoring_available():
            logger.warning("Monitoring requested but not available")
        
        logger.info(f"TrinoExperiment initialized: {config.name}")
    
    def prepare(self) -> None:
        """
        Prepare the experiment (validate config, check dependencies).
        
        Raises:
            ValueError: If configuration is invalid
            QueryExecutionError: If connection test fails
        """
        logger.info(f"Preparing experiment: {self.config.name}")
        
        # Validate configuration
        if not self.config.queries and not self.config.query_files:
            raise ValueError("No queries specified in experiment configuration")
        
        # Test Trino connection
        try:
            self.executor.connect()
            logger.info("Successfully connected to Trino")
            
            # Execute a simple test query
            test_query = "SELECT 1 as test"
            _, metadata = self.executor.execute_query(test_query, fetch_results=False)
            
            if not metadata.get("success"):
                raise QueryExecutionError("Test query failed")
            
            logger.info("Connection test passed")
            logger.info("Experiment preparation completed successfully")
            
        except Exception as e:
            logger.error(f"Preparation failed: {e}")
            self.executor.disconnect()
            raise
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the experiment.
        
        Returns:
            Dictionary containing experiment results
            
        Raises:
            QueryExecutionError: If execution fails
        """
        logger.info(f"Starting experiment execution: {self.config.name}")
        
        self.start_time = datetime.now()
        self.status = "running"
        
        # Create experiment record in database
        self.experiment_id = self._create_experiment_record()
        
        # Start monitoring
        self._start_monitoring()
        
        try:
            # Ensure connected to Trino
            if not self.executor.is_connected():
                self.executor.connect()
            
            # Collect all queries to execute
            queries = self._collect_queries()
            logger.info(f"Prepared {len(queries)} queries for execution")
            
            # Execute warmup runs
            if self.config.warmup_runs > 0:
                logger.info(f"Executing {self.config.warmup_runs} warmup runs")
                self._execute_warmup_runs(queries)
            
            # Execute measured runs
            logger.info(f"Executing {self.config.runs} measured runs")
            self._execute_measured_runs(queries)
            
            self.end_time = datetime.now()
            self.status = "completed"
            
            # Stop monitoring and save metrics
            monitoring_file = self._stop_monitoring_and_collect(self.current_run_id)
            
            # Build results
            self.results = self._build_results_dict(
                duration=self.get_duration(),
                queries_count=len(queries),
                monitoring_file=monitoring_file,
            )
            
            logger.info(f"Experiment completed successfully: {self.config.name}")
            return self.results
            
        except Exception as e:
            self.end_time = datetime.now()
            self.status = "failed"
            logger.error(f"Experiment failed: {e}")
            
            # Stop monitoring on failure
            if self.enable_monitoring and self.monitoring_session:
                try:
                    self.monitoring_session.stop()
                    self.monitoring_session.save_metrics()
                except Exception as me:
                    logger.error(f"Failed to save monitoring data after failure: {me}")
            
            self.results = {
                "experiment_name": self.config.name,
                "status": "failed",
                "error": str(e),
                "runs_completed": len(self.run_results) if self.run_results else self.total_queries_executed,
            }
            raise
            
        finally:
            self.executor.disconnect()

    def _collect_queries(self) -> List[Dict[str, Any]]:
        """
        Collect all queries from inline and file sources.
        
        Returns:
            List of query dictionaries with 'sql', 'name', 'source' keys
        """
        return collect_queries(
            inline_queries=self.config.queries,
            query_files=self.config.query_files,
        )
    
    def _execute_warmup_runs(self, queries: List[Dict[str, Any]]) -> None:
        """Execute warmup runs (not measured)."""
        for run_num in range(self.config.warmup_runs):
            logger.info(f"Warmup run {run_num + 1}/{self.config.warmup_runs}")
            for query in queries:
                try:
                    self.executor.execute_query(query["sql"], fetch_results=False)
                except Exception as e:
                    logger.warning(f"Warmup query failed: {e}")
    
    def _execute_measured_runs(self, queries: List[Dict[str, Any]]) -> None:
        """Execute measured runs and collect results."""
        parallel_queries = getattr(self.config, 'parallel_queries', 1)
        
        for run_num in range(self.config.runs):
            logger.info(f"Measured run {run_num + 1}/{self.config.runs}")
            
            # Create run record in database
            if self.experiment_id:
                self.current_run_id = self._create_run_record(self.experiment_id)
            
            run_queries_succeeded = 0
            run_queries_failed = 0
            
            # Choose execution mode
            if parallel_queries > 1:
                logger.info(f"Executing {len(queries)} queries in parallel (max {parallel_queries} concurrent)")
                results = self._execute_queries_parallel(queries, run_num, parallel_queries)
                for result in results:
                    if result['status'] == 'success':
                        run_queries_succeeded += 1
                    else:
                        run_queries_failed += 1
            else:
                # Sequential execution
                for query in queries:
                    result = self._execute_single_query(query, run_num)
                    if result['status'] == 'success':
                        run_queries_succeeded += 1
                    else:
                        run_queries_failed += 1
            
            # Complete run record
            if self.current_run_id:
                self._complete_run_record(self.current_run_id)
    
    def _execute_single_query(self, query: Dict[str, Any], run_num: int) -> Dict[str, Any]:
        """
        Execute a single query and record results.
        
        Args:
            query: Query dictionary with 'name', 'sql', 'source'
            run_num: Current run number (0-indexed)
            
        Returns:
            Result dictionary with 'status', 'duration', 'metadata'
        """
        query_name = f"{query['name']}_run{run_num + 1}"
        logger.info(f"Executing: {query_name}")
        
        query_exec_start = time.time()
        status = "success"
        error = None
        query_metadata = None
        
        try:
            _, query_metadata = self.executor.execute_query_with_retry(
                query["sql"],
                fetch_results=True
            )
            
            # Track query in monitoring
            if query_metadata and query_metadata.get("query_id"):
                self._track_query_in_monitoring(query_metadata["query_id"])
            
        except Exception as e:
            status = "failed"
            error = e
            logger.error(f"Query {query_name} failed: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        query_duration = time.time() - query_exec_start
        self.total_queries_executed += 1
        
        # Save to database
        if self.current_run_id:
            self._save_query_execution(
                run_id=self.current_run_id,
                query_name=query["name"],
                query_sql=query["sql"],
                duration=query_duration,
                status=status,
                error=error,
                query_metadata=query_metadata,
            )
        
        # Save to JSON
        self._save_query_to_json(
            query_name=query["name"],
            query_source=query["source"],
            run_number=run_num + 1,
            duration=query_duration,
            status=status,
            error=error,
            query_metadata=query_metadata,
        )
        
        return {
            'status': status,
            'duration': query_duration,
            'metadata': query_metadata,
            'error': error,
        }
    
    def validate(self) -> bool:
        """
        Validate experiment results.
        
        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating experiment results")
        
        # Get results from database if enabled
        if self.enable_database and self.result_storage and self.experiment_id:
            return self._validate_from_database()
        else:
            return self._validate_from_memory()
    
    def _validate_from_database(self) -> bool:
        """Validate results from database records."""
        try:
            runs = self.result_storage.get_experiment_runs(self.experiment_id)
            if not runs:
                logger.warning("No results to validate")
                return False
            
            all_query_executions = []
            for run in runs:
                query_execs = self.result_storage.get_run_query_executions(run['id'])
                all_query_executions.extend(query_execs)
            
            if not all_query_executions:
                logger.warning("No query executions to validate")
                return False
            
            return self._check_validation_rules(
                executions=all_query_executions,
                get_status=lambda q: q.get('status'),
                get_time=lambda q: q.get('execution_time'),
                status_success='completed',
            )
            
        except Exception as e:
            logger.error(f"Failed to validate from database: {e}")
            return False
    
    def _validate_from_memory(self) -> bool:
        """Validate results from in-memory results."""
        if not self.run_results:
            logger.warning("No results to validate")
            return False
        
        return self._check_validation_rules(
            executions=self.run_results,
            get_status=lambda r: r.status,
            get_time=lambda r: r.execution_time,
            status_success='success',
        )
    
    def _check_validation_rules(
        self,
        executions: List,
        get_status,
        get_time,
        status_success: str,
    ) -> bool:
        """
        Check validation rules against executions.
        
        Delegates to the extracted validate_results function.
        """
        return validate_results(
            executions=executions,
            validation_rules=self.config.validation or {},
            get_status=get_status,
            get_time=get_time,
            status_success=status_success,
        )
    
    def cleanup(self) -> None:
        """Clean up resources after experiment completion."""
        logger.info("Cleaning up experiment resources")
        
        try:
            # Close connection pool
            self._cleanup_connection_pool()
            
            # Close main executor connection
            if self.executor.is_connected():
                self.executor.disconnect()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
        
        logger.info("Cleanup completed")
