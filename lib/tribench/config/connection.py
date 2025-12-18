"""
Connection configuration for Trino and other database systems.

Provides a standardized way to handle database connections across the framework,
eliminating duplicated connection handling code.
"""

import logging
import threading
import queue
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

import trino.dbapi

from tribench.defaults import Defaults

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """
    Configuration for database connections (primarily Trino).
    
    Provides a standardized, type-safe way to manage connection parameters
    across the framework instead of passing around dictionaries.
    
    Attributes:
        host: Database host address
        port: Database port number
        user: Username for authentication
        catalog: Default catalog/database name
        schema: Default schema name
        http_scheme: HTTP scheme (http or https)
        
    Example:
        # Create from defaults
        config = ConnectionConfig.from_defaults()
        
        # Create from dict
        config = ConnectionConfig.from_dict({
            'host': 'localhost',
            'port': 8080,
            'user': 'admin'
        })
        
        # Create connection
        conn = config.connect()
        
        # Use in context manager
        with config.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """
    
    host: str
    port: int
    user: str
    catalog: str = Defaults.Trino.CATALOG
    schema: str = Defaults.Trino.SCHEMA
    http_scheme: str = "http"
    
    @classmethod
    def from_defaults(cls) -> 'ConnectionConfig':
        """
        Create ConnectionConfig using framework defaults.
        
        Returns:
            ConnectionConfig with default values from Defaults.Trino
            
        Example:
            config = ConnectionConfig.from_defaults()
            # Uses: localhost:8080, user=tribench, catalog=memory, schema=default
        """
        return cls(
            host=Defaults.Trino.HOST,
            port=Defaults.Trino.PORT,
            user=Defaults.Trino.USER,
            catalog=Defaults.Trino.CATALOG,
            schema=Defaults.Trino.SCHEMA,
            http_scheme="http"
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConnectionConfig':
        """
        Create ConnectionConfig from a configuration dictionary.
        
        Falls back to defaults for missing values.
        
        Args:
            config_dict: Dictionary with connection parameters.
                        Supports keys: host, port, user, catalog, schema, http_scheme
        
        Returns:
            ConnectionConfig instance
            
        Example:
            config = ConnectionConfig.from_dict({
                'host': 'remote-trino.example.com',
                'port': 8443,
                'user': 'admin',
                'http_scheme': 'https'
            })
        """
        return cls(
            host=config_dict.get('host', Defaults.Trino.HOST),
            port=config_dict.get('port', Defaults.Trino.PORT),
            user=config_dict.get('user', Defaults.Trino.USER),
            catalog=config_dict.get('catalog', Defaults.Trino.CATALOG),
            schema=config_dict.get('schema', Defaults.Trino.SCHEMA),
            http_scheme=config_dict.get('http_scheme', 'http')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ConnectionConfig to a dictionary.
        
        Useful for serialization and logging.
        
        Returns:
            Dictionary representation of the connection config
            
        Example:
            config = ConnectionConfig.from_defaults()
            print(config.to_dict())
            # {'host': 'localhost', 'port': 8080, 'user': 'tribench', ...}
        """
        return asdict(self)
    
    def connect(self) -> trino.dbapi.Connection:
        """
        Create a Trino database connection using this configuration.
        
        Returns:
            Active Trino connection
            
        Raises:
            Exception: If connection fails
            
        Example:
            config = ConnectionConfig.from_defaults()
            conn = config.connect()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            finally:
                conn.close()
        """
        logger.debug(f"Connecting to Trino: {self}")
        
        connection = trino.dbapi.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            catalog=self.catalog,
            schema=self.schema,
            http_scheme=self.http_scheme,
        )
        
        logger.info(f"Connected to Trino at {self.host}:{self.port}")
        return connection
    
    def merge(self, overrides: Optional[Dict[str, Any]]) -> 'ConnectionConfig':
        """
        Create a new ConnectionConfig with overridden values.
        
        Useful for applying experiment-specific or CLI overrides.
        
        Args:
            overrides: Dictionary with values to override.
                      None values are ignored.
        
        Returns:
            New ConnectionConfig with merged values
            
        Example:
            base = ConnectionConfig.from_defaults()
            overridden = base.merge({'host': 'prod-trino', 'port': 8443})
            # base remains unchanged, overridden has new values
        """
        if not overrides:
            return self
        
        # Start with current values
        merged_dict = self.to_dict()
        
        # Apply overrides (skip None values)
        for key, value in overrides.items():
            if value is not None and key in merged_dict:
                merged_dict[key] = value
        
        return ConnectionConfig.from_dict(merged_dict)
    
    def __str__(self) -> str:
        """
        String representation for logging.
        
        Returns:
            Human-readable connection string
            
        Example:
            config = ConnectionConfig.from_defaults()
            print(config)
            # tribench@localhost:8080/memory.default
        """
        return f"{self.user}@{self.host}:{self.port}/{self.catalog}.{self.schema}"
    
    def __repr__(self) -> str:
        """
        Detailed representation for debugging.
        
        Returns:
            Detailed string representation
        """
        return (
            f"ConnectionConfig(host={self.host!r}, port={self.port}, "
            f"user={self.user!r}, catalog={self.catalog!r}, "
            f"schema={self.schema!r}, http_scheme={self.http_scheme!r})"
        )


class ConnectionPool:
    """Thread-safe connection pool for concurrent query execution.
    
    Manages a pool of database connections that can be shared across
    multiple threads for concurrent query execution.
    
    Attributes:
        config: ConnectionConfig for creating connections
        pool_size: Maximum number of connections in the pool
        timeout: Timeout for acquiring a connection from the pool
        
    Example:
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=5)
        
        # Use in context manager
        with pool.acquire() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            
        # Or manage manually
        conn = pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        finally:
            pool.release_connection(conn)
    """
    
    def __init__(self, 
                 config: ConnectionConfig,
                 pool_size: int = 5,
                 timeout: float = 30.0,
                 eager_create: bool = False):
        """Initialize connection pool.
        
        Args:
            config: ConnectionConfig to use for creating connections
            pool_size: Maximum number of connections to maintain
            timeout: Timeout in seconds for acquiring a connection
            eager_create: If True, pre-create all connections at initialization
        """
        self.config = config
        self.pool_size = pool_size
        self.timeout = timeout
        self.eager_create = eager_create
        
        # Thread-safe queue for available connections
        self._pool: queue.Queue = queue.Queue(maxsize=pool_size)
        
        # Track all connections (in use and available)
        self._all_connections: List[trino.dbapi.Connection] = []
        self._lock = threading.Lock()
        
        # Statistics
        self._created_count = 0
        self._acquired_count = 0
        self._released_count = 0
        
        logger.info(f"Connection pool initialized: size={pool_size}, config={config}, eager={eager_create}")
        
        # Eagerly create all connections if requested
        if eager_create:
            logger.info(f"Pre-creating {pool_size} connections...")
            for i in range(pool_size):
                try:
                    conn = self.config.connect()
                    self._all_connections.append(conn)
                    self._pool.put(conn)
                    self._created_count += 1
                    logger.debug(f"Pre-created connection {i+1}/{pool_size}")
                except Exception as e:
                    logger.error(f"Failed to pre-create connection {i+1}: {e}")
                    raise
            logger.info(f"Pre-created all {self._created_count} connections")
    
    def get_connection(self, timeout: Optional[float] = None) -> trino.dbapi.Connection:
        """Get a connection from the pool.
        
        If no connection is available and pool is not full, creates a new one.
        If pool is full, waits for a connection to be released.
        
        Args:
            timeout: Timeout in seconds (uses pool default if None)
            
        Returns:
            Database connection
            
        Raises:
            queue.Empty: If timeout expires while waiting
        """
        if timeout is None:
            timeout = self.timeout
        
        try:
            # Try to get existing connection from pool
            conn = self._pool.get(block=False)
            self._acquired_count += 1
            logger.debug(f"Acquired connection from pool (acquired={self._acquired_count})")
            return conn
            
        except queue.Empty:
            # No connection available, check if we can create new one
            should_create = False
            with self._lock:
                if self._created_count < self.pool_size:
                    should_create = True
                    # Reserve the slot before releasing lock
                    self._created_count += 1
            
            if should_create:
                # Create connection outside the lock to avoid blocking
                try:
                    conn = self.config.connect()
                    with self._lock:
                        self._all_connections.append(conn)
                        self._acquired_count += 1
                    logger.debug(f"Created new connection (total={self._created_count})")
                    return conn
                except Exception:
                    # Failed to create, decrement counter
                    with self._lock:
                        self._created_count -= 1
                    raise
            
            # Pool is full, wait for a connection to be released
            logger.debug(f"Waiting for connection (timeout={timeout}s)")
            conn = self._pool.get(block=True, timeout=timeout)
            self._acquired_count += 1
            logger.debug(f"Acquired connection after wait (acquired={self._acquired_count})")
            return conn
    
    def release_connection(self, conn: trino.dbapi.Connection) -> None:
        """Release a connection back to the pool.
        
        Args:
            conn: Connection to release
        """
        if conn not in self._all_connections:
            logger.warning("Attempted to release unknown connection")
            return
        
        try:
            self._pool.put(conn, block=False)
            self._released_count += 1
            logger.debug(f"Released connection to pool (released={self._released_count})")
        except queue.Full:
            logger.warning("Pool is full, cannot release connection")
    
    @contextmanager
    def acquire(self, timeout: Optional[float] = None):
        """Context manager for acquiring and releasing connections.
        
        Args:
            timeout: Timeout for acquiring connection
            
        Yields:
            Database connection
            
        Example:
            with pool.acquire() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
        """
        conn = self.get_connection(timeout=timeout)
        try:
            yield conn
        finally:
            self.release_connection(conn)
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._all_connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            
            self._all_connections.clear()
            
            # Clear the queue
            while not self._pool.empty():
                try:
                    self._pool.get(block=False)
                except queue.Empty:
                    break
            
            logger.info(f"Closed all {self._created_count} connections")
            self._created_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        return {
            "pool_size": self.pool_size,
            "created_connections": self._created_count,
            "available_connections": self._pool.qsize(),
            "in_use_connections": self._created_count - self._pool.qsize(),
            "total_acquired": self._acquired_count,
            "total_released": self._released_count,
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close all connections."""
        self.close_all()
        return False
    
    def __del__(self):
        """Destructor - ensure connections are closed."""
        try:
            self.close_all()
        except Exception:
            pass
