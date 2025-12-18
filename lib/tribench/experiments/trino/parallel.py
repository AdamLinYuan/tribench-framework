"""Parallel query execution for Trino experiments.

Handles concurrent query execution using thread pools and connection pooling.
"""

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ...config import ConnectionPool, ConnectionConfig

logger = logging.getLogger(__name__)


class ParallelExecutionMixin:
    """
    Mixin class providing parallel query execution capabilities.
    
    This mixin handles:
    - Connection pool management
    - Parallel query execution using thread pools
    - Thread-safe result collection
    
    Attributes expected from the host class:
    - connection_config: ConnectionConfig
    - executor: QueryExecutor
    - enable_monitoring: bool
    - trino_monitor: Optional[TrinoMonitor]
    - enable_database: bool
    - result_storage: Optional[ResultStorage]
    - current_run_id: Optional[int]
    - enable_json: bool
    - result_collector: ResultCollector
    - run_results: List[Result]
    - total_queries_executed: int
    - config: ExperimentConfig
    """
    
    _connection_pool: Optional['ConnectionPool'] = None
    
    def _init_connection_pool(self, pool_size: int) -> 'ConnectionPool':
        """
        Initialize or get the connection pool for parallel execution.
        
        Args:
            pool_size: Number of connections in the pool
            
        Returns:
            ConnectionPool instance
        """
        from ...config import ConnectionPool
        
        if self._connection_pool is None:
            logger.info(f"Initializing connection pool with size={pool_size}")
            self._connection_pool = ConnectionPool(
                self.connection_config,
                pool_size=pool_size,
                timeout=30.0,
                eager_create=True  # Pre-create all connections
            )
        return self._connection_pool
    
    def _execute_queries_parallel(
        self, 
        queries: List[Dict[str, Any]], 
        run_num: int,
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """
        Execute queries in parallel using a thread pool.
        
        Each thread gets its own connection from the pool.
        
        Args:
            queries: List of query dictionaries with 'name', 'sql', 'source'
            run_num: Current run number (0-indexed)
            max_workers: Maximum number of concurrent queries
            
        Returns:
            List of result dictionaries
        """
        # Initialize connection pool
        pool = self._init_connection_pool(max_workers)
        
        # Lock for thread-safe result storage
        results_lock = threading.Lock()
        
        def execute_query_task(query: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a single query using pooled connection."""
            return self._execute_parallel_query(
                query, run_num, results_lock
            )
        
        # Execute queries in parallel
        results = []
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all queries
                future_to_query = {
                    executor.submit(execute_query_task, query): query 
                    for query in queries
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_query):
                    query = future_to_query[future]
                    try:
                        result = future.result()
                        results.append(result)
                        logger.info(f"[Parallel] Completed: {result['query_name']} in {result['duration']:.2f}s")
                    except Exception as e:
                        logger.error(f"[Parallel] Query {query['name']} raised exception: {e}")
                        results.append({
                            'status': 'failed',
                            'duration': 0,
                            'metadata': None,
                            'error': e,
                            'query_name': query['name'],
                        })
        
        finally:
            # Log connection pool statistics
            if self._connection_pool:
                pool_stats = self._connection_pool.get_stats()
                logger.info(f"[Parallel] Pool stats: {pool_stats}")
        
        logger.info(f"[Parallel] Completed {len(results)} queries")
        return results
    
    def _execute_parallel_query(
        self,
        query: Dict[str, Any],
        run_num: int,
        results_lock: threading.Lock,
    ) -> Dict[str, Any]:
        """
        Execute a single query in parallel context.
        
        Args:
            query: Query dictionary with 'name', 'sql', 'source'
            run_num: Current run number (0-indexed)
            results_lock: Lock for thread-safe operations
            
        Returns:
            Result dictionary
        """
        query_name = f"{query['name']}_run{run_num + 1}"
        logger.info(f"[Parallel] Executing: {query_name}")
        
        query_exec_start = time.time()
        status = "success"
        error = None
        query_metadata = None
        
        try:
            # Use pooled execution for better connection management
            _, query_metadata = self.executor.execute_with_pool(
                query["sql"],
                self._connection_pool,
                fetch_results=True
            )
            
            # Track query in monitoring if available
            if (self.enable_monitoring and self.trino_monitor and 
                query_metadata and query_metadata.get("query_id")):
                try:
                    self.trino_monitor.track_query(query_metadata["query_id"])
                except Exception as e:
                    logger.warning(f"Failed to track query in monitoring: {e}")
            
        except Exception as e:
            status = "failed"
            error = e
            logger.error(f"[Parallel] Query {query_name} failed: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        query_duration = time.time() - query_exec_start
        
        # Thread-safe increment
        with results_lock:
            self.total_queries_executed += 1
        
        # Save to database if enabled
        if self.enable_database and self.result_storage and self.current_run_id:
            self._save_query_execution(
                run_id=self.current_run_id,
                query_name=query["name"],
                query_sql=query["sql"],
                duration=query_duration,
                status=status,
                error=error,
                query_metadata=query_metadata,
            )
        
        # Save to JSON files if enabled (thread-safe append)
        if self.enable_json:
            result_obj = self.result_collector.create_result(
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
            
            with results_lock:
                self.run_results.append(result_obj)
            
            self.result_collector.save_result(result_obj)
        
        return {
            'status': status,
            'duration': query_duration,
            'metadata': query_metadata,
            'error': error,
            'query_name': query['name'],
        }
    
    def _cleanup_connection_pool(self) -> None:
        """Clean up the connection pool."""
        if self._connection_pool is not None:
            pool_stats = self._connection_pool.get_stats()
            logger.info(f"Connection pool stats: {pool_stats}")
            self._connection_pool.close_all()
            logger.info("Connection pool closed")
            self._connection_pool = None
