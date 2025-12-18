"""Tests for connection pooling functionality."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from tribench.config import ConnectionConfig, ConnectionPool
from tribench.experiments.query_executor import QueryExecutor


class TestConnectionPool:
    """Test cases for ConnectionPool."""
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_pool_initialization(self, mock_connect):
        """Test connection pool initialization."""
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=3)
        
        assert pool.pool_size == 3
        assert pool.config == config
        assert pool._created_count == 0
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_get_connection_creates_new(self, mock_connect):
        """Test getting a connection creates a new one when pool is empty."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=3)
        
        conn = pool.get_connection()
        
        assert conn == mock_conn
        assert pool._created_count == 1
        assert pool._acquired_count == 1
        mock_connect.assert_called_once()
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_release_and_reuse_connection(self, mock_connect):
        """Test releasing and reusing a connection."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=3)
        
        # Get and release
        conn1 = pool.get_connection()
        pool.release_connection(conn1)
        
        # Get again - should reuse
        conn2 = pool.get_connection()
        
        assert conn1 == conn2
        assert pool._created_count == 1  # Only created once
        assert pool._acquired_count == 2  # Acquired twice
        assert mock_connect.call_count == 1  # Connected once
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_pool_size_limit(self, mock_connect):
        """Test that pool respects size limit."""
        import queue
        
        mock_connect.return_value = Mock()
        
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=2, timeout=0.1)
        
        # Create pool_size connections
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        
        assert pool._created_count == 2
        
        # Try to create one more - should raise queue.Empty with short timeout
        with pytest.raises(queue.Empty):
            pool.get_connection(timeout=0.1)
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_context_manager_acquire(self, mock_connect):
        """Test context manager for acquiring connections."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=3)
        
        with pool.acquire() as conn:
            assert conn == mock_conn
            assert pool._acquired_count == 1
        
        # Connection should be released
        assert pool._released_count == 1
        assert pool._pool.qsize() == 1
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_pool_stats(self, mock_connect):
        """Test pool statistics tracking."""
        mock_connect.return_value = Mock()
        
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=3)
        
        # Get some connections
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        pool.release_connection(conn1)
        
        stats = pool.get_stats()
        
        assert stats["pool_size"] == 3
        assert stats["created_connections"] == 2
        assert stats["available_connections"] == 1
        assert stats["in_use_connections"] == 1
        assert stats["total_acquired"] == 2
        assert stats["total_released"] == 1
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_close_all(self, mock_connect):
        """Test closing all connections."""
        mock_conn1 = Mock()
        mock_conn2 = Mock()
        mock_connect.side_effect = [mock_conn1, mock_conn2]
        
        config = ConnectionConfig.from_defaults()
        pool = ConnectionPool(config, pool_size=3)
        
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        pool.release_connection(conn1)
        pool.release_connection(conn2)
        
        pool.close_all()
        
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
        assert pool._created_count == 0
        assert len(pool._all_connections) == 0
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_pool_context_manager(self, mock_connect):
        """Test pool as context manager."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = ConnectionConfig.from_defaults()
        
        with ConnectionPool(config, pool_size=2) as pool:
            conn = pool.get_connection()
            assert conn == mock_conn
        
        # Should close all connections on exit
        mock_conn.close.assert_called_once()


class TestPooledQueryExecution:
    """Test cases for pooled query execution."""
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_execute_with_pool(self, mock_connect):
        """Test executing a query with connection pool."""
        # Setup mock connection and cursor
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [(1,)]
        mock_cursor.stats = {"queryId": "test_123"}
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create executor and pool
        config = ConnectionConfig.from_defaults()
        executor = QueryExecutor(connection=config)
        pool = ConnectionPool(config, pool_size=3)
        
        # Execute query
        rows, metadata = executor.execute_with_pool("SELECT 1", pool)
        
        assert rows == [(1,)]
        assert metadata["success"] is True
        assert metadata["rows_returned"] == 1
        assert metadata["pooled"] is True
        assert "query_id" in metadata
        
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.close.assert_called_once()
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_concurrent_pooled_execution(self, mock_connect):
        """Test concurrent query execution with connection pool."""
        # Setup mock
        def create_mock_conn():
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [(1,)]
            mock_cursor.stats = None
            
            mock_conn = Mock()
            mock_conn.cursor.return_value = mock_cursor
            return mock_conn
        
        # Create multiple connections
        mock_connect.side_effect = [create_mock_conn() for _ in range(3)]
        
        # Setup
        config = ConnectionConfig.from_defaults()
        executor = QueryExecutor(connection=config)
        pool = ConnectionPool(config, pool_size=3)
        
        # Execute queries concurrently
        queries = [f"SELECT {i}" for i in range(5)]
        
        with ThreadPoolExecutor(max_workers=3) as thread_pool:
            futures = [
                thread_pool.submit(executor.execute_with_pool, q, pool, True)
                for q in queries
            ]
            
            results = []
            for future in as_completed(futures):
                rows, metadata = future.result()
                results.append((rows, metadata))
        
        # All queries should complete successfully
        assert len(results) == 5
        for rows, metadata in results:
            assert metadata["success"] is True
            assert metadata["pooled"] is True
        
        # Pool should have created max 3 connections
        assert pool._created_count <= 3
        assert pool._acquired_count == 5  # But acquired 5 times total
    
    @patch('tribench.config.connection.trino.dbapi.connect')
    def test_pooled_execution_error_handling(self, mock_connect):
        """Test error handling in pooled execution."""
        from trino.exceptions import TrinoUserError
        
        # Setup mock to raise error
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = TrinoUserError("Syntax error")
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        config = ConnectionConfig.from_defaults()
        executor = QueryExecutor(connection=config)
        pool = ConnectionPool(config, pool_size=3)
        
        # Should raise QueryExecutionError
        from tribench.experiments.query_executor import QueryExecutionError
        
        with pytest.raises(QueryExecutionError):
            executor.execute_with_pool("INVALID SQL", pool)
        
        # Cursor should still be closed
        mock_cursor.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
