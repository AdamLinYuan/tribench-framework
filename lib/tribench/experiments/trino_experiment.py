"""Trino-specific experiment implementation."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.experiment import Experiment, ExperimentConfig
from ..core.result import Result
from .query_executor import QueryExecutor, QueryExecutionError
from .result_collector import ResultCollector

# Database storage imports
try:
    from ..storage import ResultStorage, init_database
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Optional monitoring imports (graceful degradation if not available)
try:
    from ..monitoring import (
        MonitoringSession,
        MonitoringConfig,
        ResourceMonitor,
        TrinoMonitor,
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring module not available - experiments will run without monitoring")


class TrinoExperiment(Experiment):
    """
    Concrete implementation of Experiment for Trino SQL workloads.
    
    Executes SQL queries against Trino, collects metrics, and validates results.
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
        conn_params = config.connection or {}
        self.executor = QueryExecutor(
            host=conn_params.get("host", "localhost"),
            port=conn_params.get("port", 8080),
            user=conn_params.get("user", "tribench"),
            catalog=conn_params.get("catalog", "memory"),
            schema=conn_params.get("schema", "default"),
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        
        # Storage configuration
        self.enable_json = enable_json
        
        # Initialize result collector (for JSON file storage when enabled)
        self.result_collector = ResultCollector(results_dir)
        
        # Storage for individual run results
        self.run_results: List[Result] = []
        
        # Track query execution counts (for both database and JSON storage modes)
        self.total_queries_executed = 0
        
        # Initialize database storage
        self.enable_database = enable_database and STORAGE_AVAILABLE
        self.result_storage: Optional[ResultStorage] = None
        self.experiment_id: Optional[int] = None
        self.current_run_id: Optional[int] = None
        
        if self.enable_database:
            try:
                # Initialize database
                init_database()
                self.result_storage = ResultStorage()
                logger.info("Database storage initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database storage: {e}")
                self.enable_database = False
        else:
            if enable_database and not STORAGE_AVAILABLE:
                logger.warning("Database storage requested but not available")
        
        # Initialize monitoring session
        self.monitoring_session: Optional['MonitoringSession'] = None
        self.enable_monitoring = enable_monitoring and MONITORING_AVAILABLE
        self.trino_monitor: Optional['TrinoMonitor'] = None
        
        if self.enable_monitoring:
            self._setup_monitoring(conn_params)
        else:
            if enable_monitoring and not MONITORING_AVAILABLE:
                logger.warning("Monitoring requested but not available")
        
        logger.info(f"TrinoExperiment initialized: {config.name}")
    
    def _setup_monitoring(self, conn_params: Dict[str, Any]) -> None:
        """
        Set up monitoring session with collectors.
        
        Args:
            conn_params: Connection parameters for Trino
        """
        try:
            # Create monitoring config
            monitoring_config = MonitoringConfig(
                enabled=True,
                interval_seconds=1.0,  # 1 second sampling
            )
            
            # Create collectors
            collectors = []
            
            # Add resource monitor
            resource_monitor = ResourceMonitor(config=monitoring_config)
            collectors.append(resource_monitor)
            
            # Add Trino monitor
            self.trino_monitor = TrinoMonitor(
                config=monitoring_config,
                host=conn_params.get("host", "localhost"),
                port=conn_params.get("port", 8080),
                username=conn_params.get("user"),
            )
            collectors.append(self.trino_monitor)
            
            # Create monitoring session
            self.monitoring_session = MonitoringSession(
                config=monitoring_config,
                collectors=collectors,
                experiment_name=self.config.name,
            )
            
            logger.info("Monitoring session initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring: {e}")
            self.enable_monitoring = False
            self.monitoring_session = None
            self.trino_monitor = None
    
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
            
        except Exception as e:
            logger.error(f"Preparation failed: {e}")
            raise
        finally:
            self.executor.disconnect()
        
        logger.info("Experiment preparation completed successfully")
    
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
        
        # Create or get experiment record in database
        if self.enable_database and self.result_storage:
            try:
                # Extract tags from metadata if available
                tags = self.config.metadata.get('tags', []) if self.config.metadata else []
                
                # Get dataset name - check multiple sources in order of preference
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
                
                self.experiment_id = self.result_storage.create_or_get_experiment(
                    name=self.config.name,
                    experiment_type="trino_query",
                    config=self.config.to_dict(),
                    dataset_name=dataset_name,
                    tags=tags,
                )
                logger.info(f"Database: Experiment record created/retrieved (ID: {self.experiment_id})")
            except Exception as e:
                logger.error(f"Failed to create experiment record in database: {e}")
                self.enable_database = False
        
        # Start monitoring
        monitoring_file = None
        if self.enable_monitoring and self.monitoring_session:
            try:
                self.monitoring_session.start()
                logger.info("Monitoring started")
            except Exception as e:
                logger.error(f"Failed to start monitoring: {e}")
                self.enable_monitoring = False
        
        try:
            # Connect to Trino
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
            if self.enable_monitoring and self.monitoring_session:
                try:
                    self.monitoring_session.stop()
                    
                    # Get all collected metrics from the monitoring session
                    with self.monitoring_session._metrics_lock:
                        all_metrics = self.monitoring_session._collected_metrics.copy()
                    
                    # Also collect any remaining metrics from collector buffers
                    for collector in self.monitoring_session.collectors:
                        if hasattr(collector, '_metrics_buffer') and collector._metrics_buffer:
                            all_metrics.extend(collector._metrics_buffer)
                    
                    monitoring_file = None
                    
                    # Save to database if enabled (primary storage)
                    if self.enable_database and self.result_storage and self.current_run_id:
                        try:
                            if all_metrics:
                                saved_count = self.result_storage.save_monitoring_metrics(
                                    run_id=self.current_run_id,
                                    metrics=all_metrics
                                )
                                logger.info(f"Database: Saved {saved_count} monitoring metrics to run {self.current_run_id}")
                            else:
                                logger.warning("No monitoring metrics collected to save to database")
                        except Exception as e:
                            logger.error(f"Failed to save monitoring metrics to database: {e}")
                    
                    # Save to JSON file only if enabled
                    if self.enable_json:
                        monitoring_file = self.monitoring_session.save_metrics()
                        logger.info(f"Monitoring data saved to: {monitoring_file}")
                    
                except Exception as e:
                    logger.error(f"Failed to save monitoring data: {e}")
            
            # Aggregate results
            aggregated = self.result_collector.aggregate_results(self.run_results)
            
            # Calculate runs completed based on storage mode
            runs_completed = len(self.run_results) if self.run_results else self.total_queries_executed
            
            self.results = {
                "experiment_name": self.config.name,
                "total_duration_seconds": self.get_duration(),
                "runs_completed": runs_completed,
                "runs_requested": self.config.runs * len(queries),
                "statistics": aggregated,
                "results": [r.to_dict() for r in self.run_results],
            }
            
            # Add monitoring summary if available
            if monitoring_file:
                self.results["monitoring"] = {
                    "enabled": True,
                    "metrics_file": str(monitoring_file),
                    "summary": self.monitoring_session.get_summary() if self.monitoring_session else {},
                }
            else:
                self.results["monitoring"] = {"enabled": False}
            
            # Add database reference if available
            if self.enable_database and self.experiment_id:
                self.results["database"] = {
                    "enabled": True,
                    "experiment_id": self.experiment_id,
                }
            else:
                self.results["database"] = {"enabled": False}
            
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
                    monitoring_file = self.monitoring_session.save_metrics()
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
            List of query dictionaries with 'sql' and 'name' keys
        """
        queries = []
        
        # Add inline queries
        for idx, query in enumerate(self.config.queries):
            # Handle both string and dict formats
            if isinstance(query, str):
                queries.append({
                    "name": f"query_{idx + 1}",
                    "sql": query,
                    "source": "inline",
                })
            elif isinstance(query, dict):
                queries.append({
                    "name": query.get("name", f"query_{idx + 1}"),
                    "sql": query["sql"],
                    "source": "inline",
                })
            else:
                logger.warning(f"Skipping invalid query format: {type(query)}")
        
        # Add queries from files
        for query_file in self.config.query_files:
            query_path = Path(query_file)
            
            # If not absolute, try multiple resolution strategies
            if not query_path.is_absolute():
                # Strategy 1: Relative to project root
                root_path = Path(__file__).parent.parent.parent.parent
                resolved_path = root_path / query_file
                
                if not resolved_path.exists():
                    # Strategy 2: Already relative to experiments/ directory
                    resolved_path = root_path / "experiments" / query_file
                
                if not resolved_path.exists():
                    logger.error(f"Query file not found: {query_file}")
                    logger.error(f"  Tried: {root_path / query_file}")
                    logger.error(f"  Tried: {root_path / 'experiments' / query_file}")
                    continue
                
                query_path = resolved_path
            
            if not query_path.exists():
                logger.error(f"Query file not found: {query_path}")
                continue
            
            try:
                sql_content = query_path.read_text()
                queries.append({
                    "name": query_path.stem,  # Filename without extension
                    "sql": sql_content,
                    "source": str(query_path),
                })
                logger.info(f"Loaded query from file: {query_path.name}")
            except Exception as e:
                logger.error(f"Failed to read query file {query_path}: {e}")
                continue
        
        return queries
    
    def _execute_warmup_runs(self, queries: List[Dict[str, Any]]) -> None:
        """Execute warmup runs (not measured)."""
        for run_num in range(self.config.warmup_runs):
            logger.info(f"Warmup run {run_num + 1}/{self.config.warmup_runs}")
            for query in queries:
                try:
                    self.executor.execute_query(query["sql"], fetch_results=False)
                except Exception as e:
                    logger.warning(f"Warmup query failed: {e}")
                    # Continue with other queries
    
    def _execute_measured_runs(self, queries: List[Dict[str, Any]]) -> None:
        """Execute measured runs and collect results."""
        for run_num in range(self.config.runs):
            logger.info(f"Measured run {run_num + 1}/{self.config.runs}")
            
            # Create run record in database
            if self.enable_database and self.result_storage and self.experiment_id:
                try:
                    self.current_run_id = self.result_storage.create_run(
                        experiment_id=self.experiment_id,
                        run_type="measured",
                        # Don't pass run_number - let it auto-calculate
                    )
                    logger.info(f"Database: Run record created (ID: {self.current_run_id})")
                except Exception as e:
                    logger.error(f"Failed to create run record in database: {e}")
            
            run_queries_succeeded = 0
            run_queries_failed = 0
            run_start_time = time.time()
            
            for query in queries:
                query_name = f"{query['name']}_run{run_num + 1}"
                logger.info(f"Executing: {query_name}")
                
                query_exec_start = time.time()
                status = "success"
                error = None
                query_metadata = None
                
                try:
                    # Execute query with retry
                    _, query_metadata = self.executor.execute_query_with_retry(
                        query["sql"],
                        fetch_results=True
                    )
                    
                    # Track query in monitoring if available
                    if (self.enable_monitoring and self.trino_monitor and 
                        query_metadata and query_metadata.get("query_id")):
                        try:
                            self.trino_monitor.track_query(query_metadata["query_id"])
                        except Exception as e:
                            logger.warning(f"Failed to track query in monitoring: {e}")
                    
                    run_queries_succeeded += 1
                    
                except Exception as e:
                    status = "failed"
                    error = e
                    run_queries_failed += 1
                    logger.error(f"Query {query_name} failed: {e}")
                    # Log the full traceback for debugging
                    import traceback
                    logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                query_duration = time.time() - query_exec_start
                
                # Increment total queries executed counter
                self.total_queries_executed += 1
                
                # Save query execution to database (primary storage)
                if self.enable_database and self.result_storage and self.current_run_id:
                    try:
                        from datetime import datetime, timedelta
                        query_end_time = datetime.now()
                        query_start_time = query_end_time - timedelta(seconds=query_duration)
                        
                        self.result_storage.add_query_execution(
                            run_id=self.current_run_id,
                            query_name=query["name"],
                            query_text=query["sql"],
                            start_time=query_start_time,
                            end_time=query_end_time,
                            execution_time=query_duration,
                            status="completed" if status == "success" else "failed",
                            error_message=str(error) if error else None,
                            query_id=query_metadata.get("query_id") if query_metadata else None,
                            metadata=query_metadata if query_metadata else None,
                        )
                    except Exception as e:
                        logger.error(f"Failed to save query execution to database: {e}")
                
                # Save to JSON files if enabled
                if self.enable_json:
                    result = self.result_collector.create_result(
                        experiment_name=self.config.name,
                        experiment_type="trino_query",
                        duration_seconds=query_duration,
                        status=status,
                        query_metadata=query_metadata,
                        error=error,
                        metadata={
                            "query_name": query["name"],
                            "run_number": run_num + 1,
                            "query_source": query["source"],
                        }
                    )
                    
                    # Store result
                    self.run_results.append(result)
                    
                    # Save individual result as JSON file
                    self.result_collector.save_result(result)
            
            # Complete run record in database
            if self.enable_database and self.result_storage and self.current_run_id:
                try:
                    self.result_storage.complete_run(
                        run_id=self.current_run_id,
                        status="completed",
                    )
                    logger.info(f"Database: Run completed (ID: {self.current_run_id})")
                except Exception as e:
                    logger.error(f"Failed to complete run record in database: {e}")
    
    def validate(self) -> bool:
        """
        Validate experiment results.
        
        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating experiment results")
        
        # Get results from database if enabled, otherwise use in-memory results
        if self.enable_database and self.result_storage and self.experiment_id:
            try:
                # Get all query executions from database for this experiment
                runs = self.result_storage.get_experiment_runs(self.experiment_id)
                if not runs:
                    logger.warning("No results to validate")
                    logger.warning(f"Experiment ID {self.experiment_id} has no runs in database")
                    return False
                
                # Collect all query executions from all runs
                all_query_executions = []
                for run in runs:
                    query_execs = self.result_storage.get_run_query_executions(run['id'])
                    all_query_executions.extend(query_execs)
                
                if not all_query_executions:
                    logger.warning("No query executions to validate")
                    logger.warning(f"Experiment has {len(runs)} runs but no query executions recorded")
                    return False
                
                validation_rules = self.config.validation or {}
                
                # Check success rate
                min_success_rate = validation_rules.get("min_success_rate", 0.95)
                success_count = sum(1 for q in all_query_executions if q.get('status') == "completed")
                actual_success_rate = success_count / len(all_query_executions)
                
                logger.info(f"Validation check: {success_count}/{len(all_query_executions)} queries completed successfully ({actual_success_rate:.1%})")
                
                if actual_success_rate < min_success_rate:
                    logger.error(
                        f"Validation FAILED: Success rate {actual_success_rate:.2%} "
                        f"is below minimum required {min_success_rate:.2%}"
                    )
                    logger.error(f"Query statuses: {[q.get('status') for q in all_query_executions]}")
                    return False
                
                # Check execution time variance (if multiple successful runs)
                max_variance = validation_rules.get("max_execution_time_variance", 0.2)  # 20%
                successful_times = [
                    q.get('execution_time') for q in all_query_executions 
                    if q.get('status') == "completed" and q.get('execution_time') is not None
                ]
                
                if len(successful_times) > 1:
                    import statistics
                    mean_time = statistics.mean(successful_times)
                    stdev_time = statistics.stdev(successful_times)
                    coefficient_of_variation = stdev_time / mean_time if mean_time > 0 else 0
                    
                    if coefficient_of_variation > max_variance:
                        logger.warning(
                            f"Execution time variance {coefficient_of_variation:.2%} "
                            f"above maximum {max_variance:.2%}"
                        )
                        # Don't fail validation, just warn
                
                logger.info("Validation passed")
                return True
                
            except Exception as e:
                logger.error(f"Failed to validate from database: {e}")
                return False
        else:
            # Fallback to JSON-based validation
            if not self.run_results:
                logger.warning("No results to validate")
                return False
            
            validation_rules = self.config.validation or {}
            
            # Check success rate
            min_success_rate = validation_rules.get("min_success_rate", 0.95)
            success_count = sum(1 for r in self.run_results if r.status == "success")
            actual_success_rate = success_count / len(self.run_results)
            
            if actual_success_rate < min_success_rate:
                logger.error(
                    f"Success rate {actual_success_rate:.2%} "
                    f"below minimum {min_success_rate:.2%}"
                )
                return False
            
            # Check execution time variance (if multiple successful runs)
            max_variance = validation_rules.get("max_execution_time_variance", 0.2)  # 20%
            successful_times = [
                r.execution_time for r in self.run_results 
                if r.status == "success" and r.execution_time is not None
            ]
            
            if len(successful_times) > 1:
                import statistics
                mean_time = statistics.mean(successful_times)
                stdev_time = statistics.stdev(successful_times)
                coefficient_of_variation = stdev_time / mean_time if mean_time > 0 else 0
                
                if coefficient_of_variation > max_variance:
                    logger.warning(
                        f"Execution time variance {coefficient_of_variation:.2%} "
                        f"above maximum {max_variance:.2%}"
                    )
                    # Don't fail validation, just warn
            
            logger.info("Validation passed")
            return True
    
    def cleanup(self) -> None:
        """Clean up resources after experiment completion."""
        logger.info("Cleaning up experiment resources")
        
        try:
            if self.executor.is_connected():
                self.executor.disconnect()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
        
        logger.info("Cleanup completed")

