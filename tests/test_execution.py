"""Tests for QueryExecutor — all Trino I/O is mocked."""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from tribench.experiments.query_executor import (
    QueryExecutor,
    QueryExecutionError,
    QueryTimeoutError,
)
from tribench.config.connection import ConnectionConfig
from tribench.defaults import Defaults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_cursor(rows=None, stats=None):
    """Return a mock Trino cursor."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows or [(1,)]
    cursor.stats = stats or {}
    return cursor


def _make_mock_connection(cursor=None):
    """Return a mock Trino connection."""
    conn = MagicMock()
    conn.cursor.return_value = cursor or _make_mock_cursor()
    return conn


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestQueryExecutorInit:
    def test_default_uses_framework_defaults(self):
        executor = QueryExecutor()
        assert executor.config.host == Defaults.Trino.HOST
        assert executor.config.port == Defaults.Trino.PORT

    def test_init_with_connection_config(self):
        cfg = ConnectionConfig(host="remote", port=9090, user="u")
        executor = QueryExecutor(connection=cfg)
        assert executor.config.host == "remote"
        assert executor.config.port == 9090

    def test_init_with_dict(self):
        executor = QueryExecutor(connection={"host": "dict-host", "port": 7070})
        assert executor.config.host == "dict-host"

    def test_init_with_individual_params(self):
        executor = QueryExecutor(host="old-style", port=1234, user="admin")
        assert executor.config.host == "old-style"
        assert executor.config.port == 1234

    def test_init_with_invalid_type_raises(self):
        with pytest.raises(TypeError):
            QueryExecutor(connection=12345)

    def test_custom_timeout_and_retries(self):
        executor = QueryExecutor(timeout_seconds=30, max_retries=5)
        assert executor.timeout_seconds == 30
        assert executor.max_retries == 5


# ---------------------------------------------------------------------------
# connect / disconnect / is_connected
# ---------------------------------------------------------------------------

class TestQueryExecutorConnection:
    def test_connect_sets_connection_and_cursor(self):
        mock_conn = _make_mock_connection()
        with patch("tribench.config.connection.trino.dbapi.connect", return_value=mock_conn):
            executor = QueryExecutor()
            executor.connect()
            assert executor.is_connected()

    def test_disconnect_clears_connection(self):
        mock_conn = _make_mock_connection()
        with patch("tribench.config.connection.trino.dbapi.connect", return_value=mock_conn):
            executor = QueryExecutor()
            executor.connect()
            executor.disconnect()
            assert not executor.is_connected()

    def test_not_connected_initially(self):
        executor = QueryExecutor()
        assert not executor.is_connected()


# ---------------------------------------------------------------------------
# execute_query
# ---------------------------------------------------------------------------

class TestExecuteQuery:
    def _make_executor(self, rows=None, stats=None):
        mock_cursor = _make_mock_cursor(rows=rows, stats=stats)
        mock_conn = _make_mock_connection(cursor=mock_cursor)
        executor = QueryExecutor()
        executor._connection = mock_conn
        executor._cursor = mock_cursor
        return executor, mock_cursor

    def test_returns_rows_and_metadata(self):
        executor, cursor = self._make_executor(rows=[(1,), (2,)])
        rows, meta = executor.execute_query("SELECT 1")
        assert rows == [(1,), (2,)]
        assert meta["success"] is True
        assert meta["rows_returned"] == 2

    def test_metadata_includes_execution_time(self):
        executor, _ = self._make_executor()
        _, meta = executor.execute_query("SELECT 1")
        assert meta["execution_time_seconds"] >= 0

    def test_cursor_stats_are_propagated(self):
        stats = {
            "queryId": "20240101_123456_00001",
            "cpuTimeMillis": 500,
            "processedRows": 1000,
        }
        executor, _ = self._make_executor(stats=stats)
        _, meta = executor.execute_query("SELECT 1")
        assert meta.get("query_id") == "20240101_123456_00001"
        assert meta.get("cpu_time_ms") == 500

    def test_fetch_results_false_returns_empty(self):
        executor, _ = self._make_executor(rows=[(1,)])
        rows, meta = executor.execute_query("SELECT 1", fetch_results=False)
        assert rows == []
        assert meta["rows_returned"] == 0

    def test_trino_user_error_raises_query_execution_error(self):
        from trino.exceptions import TrinoUserError
        executor = QueryExecutor()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = TrinoUserError(
            {"errorCode": {"code": 1, "name": "SYNTAX_ERROR", "type": "USER_ERROR"},
             "message": "bad SQL", "errorName": "SYNTAX_ERROR", "errorType": "USER_ERROR"},
            "SELECT bad sql"
        )
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        executor._connection = mock_conn
        executor._cursor = mock_cursor

        with pytest.raises(QueryExecutionError):
            executor.execute_query("SELECT bad sql")

    def test_generic_error_raises_query_execution_error(self):
        executor = QueryExecutor()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = RuntimeError("connection lost")
        executor._connection = MagicMock()
        executor._cursor = mock_cursor

        with pytest.raises(QueryExecutionError):
            executor.execute_query("SELECT 1")


# ---------------------------------------------------------------------------
# execute_query_with_retry
# ---------------------------------------------------------------------------

class TestExecuteQueryWithRetry:
    def test_succeeds_on_first_attempt(self):
        executor = QueryExecutor(max_retries=2)
        mock_cursor = _make_mock_cursor(rows=[(42,)])
        executor._connection = MagicMock()
        executor._cursor = mock_cursor
        rows, meta = executor.execute_query_with_retry("SELECT 42")
        assert rows == [(42,)]
        assert meta.get("retry_attempts") == 0

    def test_retries_on_transient_failure(self):
        """Fail twice, succeed on third attempt."""
        executor = QueryExecutor(max_retries=3)
        call_count = [0]
        mock_cursor = MagicMock()

        def side_effect(query):
            call_count[0] += 1
            if call_count[0] < 3:
                raise QueryExecutionError("transient")

        mock_cursor.execute.side_effect = side_effect
        mock_cursor.fetchall.return_value = [(1,)]
        mock_cursor.stats = {}
        executor._connection = MagicMock()
        executor._cursor = mock_cursor

        with patch("time.sleep"):  # skip actual sleep
            rows, meta = executor.execute_query_with_retry("SELECT 1")

        assert meta.get("retry_attempts") == 2

    def test_raises_after_max_retries_exhausted(self):
        executor = QueryExecutor(max_retries=1)
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = QueryExecutionError("always fails")
        executor._connection = MagicMock()
        executor._cursor = mock_cursor

        with patch("time.sleep"):
            with pytest.raises(QueryExecutionError, match="attempts"):
                executor.execute_query_with_retry("SELECT 1")

    def test_user_error_not_retried(self):
        """A user_error embedded in the message should stop retrying immediately."""
        executor = QueryExecutor(max_retries=3)
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = QueryExecutionError("user_error: bad syntax")
        executor._connection = MagicMock()
        executor._cursor = mock_cursor

        with patch("time.sleep"):
            with pytest.raises(QueryExecutionError):
                executor.execute_query_with_retry("SELECT bad")
        # Should only have been called once
        assert mock_cursor.execute.call_count == 1


# ---------------------------------------------------------------------------
# execute_file
# ---------------------------------------------------------------------------

class TestExecuteFile:
    def test_executes_query_from_file(self, tmp_path):
        sql_file = tmp_path / "q01.sql"
        sql_file.write_text("SELECT 1")

        executor = QueryExecutor()
        mock_cursor = _make_mock_cursor(rows=[(1,)])
        executor._connection = MagicMock()
        executor._cursor = mock_cursor

        rows, meta = executor.execute_file(sql_file)
        assert rows == [(1,)]
        mock_cursor.execute.assert_called_once_with("SELECT 1")

    def test_missing_file_raises_file_not_found(self, tmp_path):
        # The missing-file check is before the try block, so FileNotFoundError propagates
        executor = QueryExecutor()
        executor._connection = MagicMock()
        executor._cursor = MagicMock()
        with pytest.raises(FileNotFoundError, match="Query file not found"):
            executor.execute_file(tmp_path / "missing.sql")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestQueryExecutorContextManager:
    def test_enter_connects(self):
        mock_conn = _make_mock_connection()
        with patch("tribench.config.connection.trino.dbapi.connect", return_value=mock_conn):
            with QueryExecutor() as executor:
                assert executor.is_connected()

    def test_exit_disconnects(self):
        mock_conn = _make_mock_connection()
        with patch("tribench.config.connection.trino.dbapi.connect", return_value=mock_conn):
            with QueryExecutor() as executor:
                pass
            assert not executor.is_connected()
