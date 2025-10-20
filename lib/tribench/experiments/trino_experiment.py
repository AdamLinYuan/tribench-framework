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

logger = logging.getLogger(__name__)


class TrinoExperiment(Experiment):
    """
    Concrete implementation of Experiment for Trino SQL workloads.
    
    Executes SQL queries against Trino, collects metrics, and validates results.
    """
    
    def __init__(self, 
                 config: ExperimentConfig,
                 results_dir: Optional[Path] = None):
        """
        Initialize a TrinoExperiment.
        
        Args:
            config: Experiment configuration
            results_dir: Directory to store results (optional)
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
        
        # Initialize result collector
        self.result_collector = ResultCollector(results_dir)
        
        # Storage for individual run results
        self.run_results: List[Result] = []
        
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
            
            # Aggregate results
            aggregated = self.result_collector.aggregate_results(self.run_results)
            
            self.results = {
                "experiment_name": self.config.name,
                "total_duration_seconds": self.get_duration(),
                "runs_completed": len(self.run_results),
                "runs_requested": self.config.runs * len(queries),
                "statistics": aggregated,
                "results": [r.to_dict() for r in self.run_results],
            }
            
            logger.info(f"Experiment completed successfully: {self.config.name}")
            return self.results
            
        except Exception as e:
            self.end_time = datetime.now()
            self.status = "failed"
            logger.error(f"Experiment failed: {e}")
            
            self.results = {
                "experiment_name": self.config.name,
                "status": "failed",
                "error": str(e),
                "runs_completed": len(self.run_results),
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
            
            for query in queries:
                query_name = f"{query['name']}_run{run_num + 1}"
                logger.info(f"Executing: {query_name}")
                
                run_start = time.time()
                status = "success"
                error = None
                query_metadata = None
                
                try:
                    # Execute query with retry
                    _, query_metadata = self.executor.execute_query_with_retry(
                        query["sql"],
                        fetch_results=True
                    )
                    
                except Exception as e:
                    status = "failed"
                    error = e
                    logger.error(f"Query {query_name} failed: {e}")
                    # Log the full traceback for debugging
                    import traceback
                    logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                run_duration = time.time() - run_start
                
                # Create result
                result = self.result_collector.create_result(
                    experiment_name=self.config.name,
                    experiment_type="trino_query",
                    duration_seconds=run_duration,
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
                
                # Save individual result
                self.result_collector.save_result(result)
    
    def validate(self) -> bool:
        """
        Validate experiment results.
        
        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating experiment results")
        
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

