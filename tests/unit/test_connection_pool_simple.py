"""Simple tests for connection pooling - non-blocking version."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tribench.config import ConnectionConfig, ConnectionPool


def test_pool_basic_creation():
    """Test that pool can be created."""
    config = ConnectionConfig.from_defaults()
    pool = ConnectionPool(config, pool_size=3)
    
    assert pool.pool_size == 3
    assert pool._created_count == 0


def test_pool_stats():
    """Test pool statistics."""
    config = ConnectionConfig.from_defaults()
    pool = ConnectionPool(config, pool_size=5)
    
    stats = pool.get_stats()
    assert stats["pool_size"] == 5
    assert stats["created_connections"] == 0
    assert stats["available_connections"] == 0


@patch('trino.dbapi.connect')
def test_connection_creation_and_release(mock_connect):
    """Test creating and releasing a connection."""
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    
    config = ConnectionConfig.from_defaults()
    pool = ConnectionPool(config, pool_size=3)
    
    # Get connection - should create new one
    conn = pool.get_connection()
    assert conn == mock_conn
    assert pool._created_count == 1
    
    # Release it
    pool.release_connection(conn)
    assert pool._released_count == 1
    
    # Close pool
    pool.close_all()
    mock_conn.close.assert_called_once()


@patch('trino.dbapi.connect')
def test_pool_context_manager_basic(mock_connect):
    """Test pool context manager."""
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    
    config = ConnectionConfig.from_defaults()
    
    with ConnectionPool(config, pool_size=2) as pool:
        conn = pool.get_connection()
        assert conn == mock_conn
    
    # Should close on exit
    mock_conn.close.assert_called_once()


@patch('trino.dbapi.connect')
def test_acquire_context_manager(mock_connect):
    """Test acquire context manager."""
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    
    config = ConnectionConfig.from_defaults()
    pool = ConnectionPool(config, pool_size=2)
    
    with pool.acquire() as conn:
        assert conn == mock_conn
    
    # Should be released
    assert pool._released_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
