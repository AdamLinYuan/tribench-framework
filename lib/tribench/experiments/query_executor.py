"""Query execution engine for Trino."""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import trino
from trino.exceptions import TrinoUserError, TrinoQueryError

from ..defaults import Defaults
from ..config import ConnectionConfig, ConnectionPool

logger = logging.getLogger(__name__)


class QueryExecutionError(Exception):
    """Raised when query execution fails."""
    pass


class QueryTimeoutError(QueryExecutionError):
    """Raised when query execution times out."""
    pass


class QueryExecutor:
    """
    Executes SQL queries against Trino with connection management,
    retry logic, and timeout handling.
    """
    
    def __init__(self, 
                 connection: Optional[Union[ConnectionConfig, Dict[str, Any]]] = None,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 user: Optional[str] = None,
                 catalog: Optional[str] = None,
                 schema: Optional[str] = None,
                 timeout_seconds: int = Defaults.Timeouts.QUERY,
                 max_retries: int = Defaults.Retry.DEFAULT_MAX_RETRIES):
        """
        Initialize the QueryExecutor.
        
        Args:
            connection: ConnectionConfig instance or dict with connection params.
                       If provided, individual params (host, port, etc.) are ignored.
            host: Trino coordinator host (deprecated, use connection param)
            port: Trino coordinator port (deprecated, use connection param)
            user: Trino user (deprecated, use connection param)
            catalog: Default catalog (deprecated, use connection param)
            schema: Default schema (deprecated, use connection param)
            timeout_seconds: Query execution timeout
            max_retries: Maximum number of retry attempts
            
        Examples:
            # New style with ConnectionConfig
            config = ConnectionConfig.from_defaults()
            executor = QueryExecutor(connection=config)
            
            # New style with dict
            executor = QueryExecutor(connection={'host': 'localhost', 'port': 8080})
            
            # Old style (backward compatible)
            executor = QueryExecutor(host='localhost', port=8080, user='admin')
        """
        # Handle connection parameter (new style)
        if connection is not None:
            if isinstance(connection, ConnectionConfig):
                self.config = connection
            elif isinstance(connection, dict):
                self.config = ConnectionConfig.from_dict(connection)
            else:
                raise TypeError(
                    f"connection must be ConnectionConfig or dict, got {type(connection)}"
                )
        # Handle individual parameters (old style, backward compatible)
        elif any(param is not None for param in [host, port, user, catalog, schema]):
            self.config = ConnectionConfig(
                host=host or Defaults.Trino.HOST,
                port=port or Defaults.Trino.PORT,
                user=user or Defaults.Trino.USER,
                catalog=catalog or Defaults.Trino.CATALOG,
                schema=schema or Defaults.Trino.SCHEMA,
            )
        # No parameters provided, use defaults
        else:
            self.config = ConnectionConfig.from_defaults()
        
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        
        self._connection: Optional[trino.dbapi.Connection] = None
        self._cursor: Optional[trino.dbapi.Cursor] = None
        
        logger.debug(f"QueryExecutor initialized: {self.config}")
    
    def connect(self) -> None:
        """
        Establish connection to Trino.
        
        Raises:
            QueryExecutionError: If connection fails
        """
        try:
            self._connection = self.config.connect()
            self._cursor = self._connection.cursor()
            logger.info(f"Connected to Trino at {self.config.host}:{self.config.port}")
            
        except Exception as e:
            raise QueryExecutionError(f"Failed to connect to Trino: {e}") from e
    
    def disconnect(self) -> None:
        """Close Trino connection."""
        if self._cursor:
            try:
                self._cursor.close()
            except Exception as e:
                logger.warning(f"Error closing cursor: {e}")
            finally:
                self._cursor = None
        
        if self._connection:
            try:
                self._connection.close()
                logger.info("Disconnected from Trino")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._connection = None
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connection is not None and self._cursor is not None
    
    def execute_query(self, 
                     query: str,
                     fetch_results: bool = True) -> Tuple[List[Tuple], Dict[str, Any]]:
        """
        Execute a SQL query with timing and statistics.
        
        Args:
            query: SQL query string
            fetch_results: Whether to fetch and return results
            
        Returns:
            Tuple of (rows, metadata) where:
                - rows: List of result tuples (if fetch_results=True)
                - metadata: Dictionary containing execution statistics
                
        Raises:
            QueryExecutionError: If query execution fails
            QueryTimeoutError: If query exceeds timeout
        """
        if not self.is_connected():
            self.connect()
        
        # Log query (safely truncate if string)
        query_preview = str(query)[:100] if query else "None"
        logger.info(f"Executing query: {query_preview}...")
        
        start_time = time.time()
        rows = []
        metadata = {
            "query": str(query) if query else None,
            "success": False,
            "execution_time_seconds": 0,
            "rows_returned": 0,
            "error": None,
        }
        
        try:
            # Execute query
            self._cursor.execute(query)
            
            # Fetch results if requested
            rows = []
            if fetch_results:
                rows = self._cursor.fetchall()
                metadata["rows_returned"] = len(rows)
            else:
                # Still need to consume the result set
                self._cursor.fetchall()
                metadata["rows_returned"] = 0
            
            # Calculate execution time
            execution_time = time.time() - start_time
            metadata["execution_time_seconds"] = execution_time
            metadata["success"] = True
            
            # Get query statistics from cursor
            if hasattr(self._cursor, 'stats') and self._cursor.stats:
                try:
                    stats = self._cursor.stats
                    metadata.update({
                        "query_id": stats.get("queryId"),
                        "state": stats.get("state"),
                        "queued_time_ms": stats.get("queuedTimeMillis"),
                        "elapsed_time_ms": stats.get("elapsedTimeMillis"),
                        "cpu_time_ms": stats.get("cpuTimeMillis"),
                        "scheduled_time_ms": stats.get("scheduledTimeMillis"),
                        "processed_rows": stats.get("processedRows"),
                        "processed_bytes": stats.get("processedBytes"),
                        "peak_memory_bytes": stats.get("peakMemoryBytes"),
                        # HIGH priority: Spill metrics for memory pressure analysis
                        "spilled_bytes": stats.get("spilledBytes"),
                        # MEDIUM priority: Parallelism metrics
                        "total_splits": stats.get("totalSplits"),
                        "completed_splits": stats.get("completedSplits"),
                    })
                except Exception as e:
                    logger.warning(f"Failed to extract query statistics: {e}")
                    # Continue without stats
            
            logger.info(f"Query completed in {execution_time:.2f}s, returned {len(rows)} rows")
            return rows, metadata
            
        except TrinoUserError as e:
            # User errors (SQL syntax, etc.)
            execution_time = time.time() - start_time
            metadata["execution_time_seconds"] = execution_time
            metadata["error"] = str(e)
            metadata["error_type"] = "user_error"
            metadata["error_code"] = e.error_code if hasattr(e, 'error_code') else None
            
            logger.error(f"Query failed with user error: {e}")
            raise QueryExecutionError(f"Query execution failed: {e}") from e
            
        except TrinoQueryError as e:
            # Query errors (runtime issues, etc.)
            execution_time = time.time() - start_time
            metadata["execution_time_seconds"] = execution_time
            metadata["error"] = str(e)
            metadata["error_type"] = "query_error"
            
            logger.error(f"Query failed with query error: {e}")
            raise QueryExecutionError(f"Query execution failed: {e}") from e
            
        except Exception as e:
            # Other errors
            execution_time = time.time() - start_time
            metadata["execution_time_seconds"] = execution_time
            metadata["error"] = str(e)
            metadata["error_type"] = "unknown_error"
            
            logger.error(f"Query failed with unexpected error: {e}")
            raise QueryExecutionError(f"Query execution failed: {e}") from e
    
    def execute_query_with_retry(self, 
                                 query: str,
                                 fetch_results: bool = True,
                                 max_retries: Optional[int] = None) -> Tuple[List[Tuple], Dict[str, Any]]:
        """
        Execute query with automatic retry on transient failures.
        
        Args:
            query: SQL query string
            fetch_results: Whether to fetch and return results
            max_retries: Max retry attempts (uses instance default if None)
            
        Returns:
            Tuple of (rows, metadata)
            
        Raises:
            QueryExecutionError: If all retry attempts fail
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{max_retries}")
                    # Exponential backoff
                    wait_time = min(2 ** attempt, 30)
                    logger.debug(f"Waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    
                    # Reconnect if connection lost
                    if not self.is_connected():
                        logger.info("Reconnecting to Trino")
                        self.connect()
                
                rows, metadata = self.execute_query(query, fetch_results)
                metadata["retry_attempts"] = attempt
                return rows, metadata
                
            except QueryExecutionError as e:
                last_error = e
                logger.warning(f"Query attempt {attempt + 1} failed: {e}")
                
                # Don't retry user errors (syntax errors, etc.)
                if "user_error" in str(e):
                    raise
                
                if attempt >= max_retries:
                    logger.error(f"All {max_retries + 1} retry attempts failed")
                    raise QueryExecutionError(
                        f"Query failed after {max_retries + 1} attempts: {last_error}"
                    ) from last_error
    
    def execute_file(self, 
                     query_file: Path,
                     fetch_results: bool = True) -> Tuple[List[Tuple], Dict[str, Any]]:
        """
        Execute SQL query from file.
        
        Args:
            query_file: Path to SQL file
            fetch_results: Whether to fetch and return results
            
        Returns:
            Tuple of (rows, metadata)
            
        Raises:
            FileNotFoundError: If query file doesn't exist
            QueryExecutionError: If query execution fails
        """
        query_file = Path(query_file)
        
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")
        
        try:
            query = query_file.read_text()
            logger.info(f"Loaded query from: {query_file}")
            return self.execute_query_with_retry(query, fetch_results)
            
        except Exception as e:
            raise QueryExecutionError(f"Failed to execute file {query_file}: {e}") from e
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
    
    def execute_with_pool(self,
                         query: str,
                         pool: ConnectionPool,
                         fetch_results: bool = True) -> Tuple[List[Tuple], Dict[str, Any]]:
        """Execute a query using a connection from the pool.
        
        This method is designed for concurrent query execution scenarios
        where multiple queries run in parallel using pooled connections.
        
        Args:
            query: SQL query string
            pool: ConnectionPool instance to use
            fetch_results: Whether to fetch and return results
            
        Returns:
            Tuple of (rows, metadata)
            
        Raises:
            QueryExecutionError: If query execution fails
            
        Example:
            config = ConnectionConfig.from_defaults()
            pool = ConnectionPool(config, pool_size=5)
            executor = QueryExecutor(connection=config)
            
            # Execute multiple queries concurrently
            from concurrent.futures import ThreadPoolExecutor
            
            queries = ["SELECT 1", "SELECT 2", "SELECT 3"]
            with ThreadPoolExecutor(max_workers=3) as thread_pool:
                futures = [
                    thread_pool.submit(executor.execute_with_pool, q, pool)
                    for q in queries
                ]
                results = [f.result() for f in futures]
        """
        query_preview = str(query)[:100] if query else "None"
        logger.info(f"Executing pooled query: {query_preview}...")
        
        start_time = time.time()
        rows = []
        metadata = {
            "query": str(query) if query else None,
            "success": False,
            "execution_time_seconds": 0,
            "rows_returned": 0,
            "error": None,
            "pooled": True,
        }
        
        try:
            # Acquire connection from pool
            with pool.acquire() as conn:
                cursor = conn.cursor()
                
                try:
                    # Execute query
                    cursor.execute(query)
                    
                    # Fetch results if requested
                    if fetch_results:
                        rows = cursor.fetchall()
                        metadata["rows_returned"] = len(rows)
                    else:
                        cursor.fetchall()
                        metadata["rows_returned"] = 0
                    
                    # Calculate execution time
                    execution_time = time.time() - start_time
                    metadata["execution_time_seconds"] = execution_time
                    metadata["success"] = True
                    
                    # Get query statistics
                    if hasattr(cursor, 'stats') and cursor.stats:
                        try:
                            stats = cursor.stats
                            metadata.update({
                                "query_id": stats.get("queryId"),
                                "state": stats.get("state"),
                                "queued_time_ms": stats.get("queuedTimeMillis"),
                                "elapsed_time_ms": stats.get("elapsedTimeMillis"),
                                "cpu_time_ms": stats.get("cpuTimeMillis"),
                                "scheduled_time_ms": stats.get("scheduledTimeMillis"),
                                "processed_rows": stats.get("processedRows"),
                                "processed_bytes": stats.get("processedBytes"),
                                "peak_memory_bytes": stats.get("peakMemoryBytes"),
                            })
                        except Exception as e:
                            logger.warning(f"Failed to extract query statistics: {e}")
                    
                    logger.info(
                        f"Pooled query completed in {execution_time:.2f}s, "
                        f"returned {len(rows)} rows"
                    )
                    
                finally:
                    cursor.close()
            
            return rows, metadata
            
        except TrinoUserError as e:
            execution_time = time.time() - start_time
            metadata["execution_time_seconds"] = execution_time
            metadata["error"] = str(e)
            metadata["error_type"] = "user_error"
            metadata["error_code"] = e.error_code if hasattr(e, 'error_code') else None
            
            logger.error(f"Pooled query failed with user error: {e}")
            raise QueryExecutionError(f"Query execution failed: {e}") from e
            
        except TrinoQueryError as e:
            execution_time = time.time() - start_time
            metadata["execution_time_seconds"] = execution_time
            metadata["error"] = str(e)
            metadata["error_type"] = "query_error"
            
            logger.error(f"Pooled query failed with query error: {e}")
            raise QueryExecutionError(f"Query execution failed: {e}") from e
            
        except Exception as e:
            execution_time = time.time() - start_time
            metadata["execution_time_seconds"] = execution_time
            metadata["error"] = str(e)
            metadata["error_type"] = "unknown_error"
            
            logger.error(f"Pooled query failed with unexpected error: {e}")
            raise QueryExecutionError(f"Query execution failed: {e}") from e

