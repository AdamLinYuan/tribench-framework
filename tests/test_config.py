"""Tests for ConnectionConfig and ConnectionPool."""

import queue
import threading
import pytest
from unittest.mock import MagicMock, patch, call

from tribench.config.connection import ConnectionConfig, ConnectionPool
from tribench.defaults import Defaults


# ---------------------------------------------------------------------------
# ConnectionConfig
# ---------------------------------------------------------------------------

class TestConnectionConfigFromDefaults:
    def test_uses_trino_defaults(self):
        cfg = ConnectionConfig.from_defaults()
        assert cfg.host == Defaults.Trino.HOST
        assert cfg.port == Defaults.Trino.PORT
        assert cfg.user == Defaults.Trino.USER
        assert cfg.catalog == Defaults.Trino.CATALOG
        assert cfg.schema == Defaults.Trino.SCHEMA
        assert cfg.http_scheme == "http"


class TestConnectionConfigFromDict:
    def test_full_dict(self):
        cfg = ConnectionConfig.from_dict({
            "host": "myhost",
            "port": 9090,
            "user": "admin",
            "catalog": "hive",
            "schema": "sales",
            "http_scheme": "https",
        })
        assert cfg.host == "myhost"
        assert cfg.port == 9090
        assert cfg.user == "admin"
        assert cfg.catalog == "hive"
        assert cfg.schema == "sales"
        assert cfg.http_scheme == "https"

    def test_partial_dict_falls_back_to_defaults(self):
        cfg = ConnectionConfig.from_dict({"host": "only-host"})
        assert cfg.host == "only-host"
        assert cfg.port == Defaults.Trino.PORT
        assert cfg.user == Defaults.Trino.USER

    def test_empty_dict_is_all_defaults(self):
        cfg = ConnectionConfig.from_dict({})
        assert cfg.host == Defaults.Trino.HOST


class TestConnectionConfigToDict:
    def test_roundtrip(self):
        cfg = ConnectionConfig(host="h", port=1234, user="u", catalog="c", schema="s")
        d = cfg.to_dict()
        cfg2 = ConnectionConfig.from_dict(d)
        assert cfg2.host == "h"
        assert cfg2.port == 1234
        assert cfg2.user == "u"

    def test_all_keys_present(self):
        cfg = ConnectionConfig.from_defaults()
        d = cfg.to_dict()
        for key in ("host", "port", "user", "catalog", "schema", "http_scheme"):
            assert key in d


class TestConnectionConfigMerge:
    def test_merge_none_returns_same(self):
        cfg = ConnectionConfig.from_defaults()
        merged = cfg.merge(None)
        assert merged is cfg

    def test_merge_empty_dict_returns_same(self):
        cfg = ConnectionConfig.from_defaults()
        merged = cfg.merge({})
        assert merged is cfg

    def test_merge_overrides_host(self):
        cfg = ConnectionConfig.from_defaults()
        merged = cfg.merge({"host": "new-host"})
        assert merged.host == "new-host"
        assert merged.port == cfg.port  # unchanged

    def test_merge_does_not_mutate_original(self):
        cfg = ConnectionConfig.from_defaults()
        original_host = cfg.host
        cfg.merge({"host": "changed"})
        assert cfg.host == original_host

    def test_merge_ignores_unknown_keys(self):
        cfg = ConnectionConfig.from_defaults()
        # unknown key "timeout" should not crash
        merged = cfg.merge({"host": "x", "timeout": 999})
        assert merged.host == "x"

    def test_merge_ignores_none_values(self):
        cfg = ConnectionConfig(host="h", port=80, user="u")
        merged = cfg.merge({"host": None})
        assert merged.host == "h"


class TestConnectionConfigStrings:
    def test_str_format(self):
        cfg = ConnectionConfig(host="myhost", port=8080, user="alice",
                               catalog="iceberg", schema="tpch")
        s = str(cfg)
        assert "alice" in s
        assert "myhost" in s
        assert "8080" in s
        assert "iceberg" in s
        assert "tpch" in s

    def test_repr_contains_all_fields(self):
        cfg = ConnectionConfig.from_defaults()
        r = repr(cfg)
        assert "ConnectionConfig" in r
        assert "host=" in r
        assert "port=" in r


class TestConnectionConfigConnect:
    def test_connect_calls_trino_dbapi(self):
        with patch("trino.dbapi.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            cfg = ConnectionConfig(host="h", port=8080, user="u")
            conn = cfg.connect()
            mock_connect.assert_called_once_with(
                host="h", port=8080, user="u",
                catalog=cfg.catalog, schema=cfg.schema,
                http_scheme="http",
            )
            assert conn is mock_conn


# ---------------------------------------------------------------------------
# ConnectionPool
# ---------------------------------------------------------------------------

def make_pool(pool_size=3, mock_connect=None):
    """Helper: build a ConnectionPool with a mocked config.connect."""
    cfg = MagicMock(spec=ConnectionConfig)
    if mock_connect is not None:
        cfg.connect.side_effect = mock_connect
    else:
        cfg.connect.side_effect = lambda: MagicMock(name="conn")
    return ConnectionPool(cfg, pool_size=pool_size, timeout=5.0)


class TestConnectionPoolInit:
    def test_init_default_state(self):
        pool = make_pool()
        assert pool.pool_size == 3
        assert pool._created_count == 0
        assert pool._acquired_count == 0
        assert pool._released_count == 0

    def test_eager_create_pre_fills_pool(self):
        pool = make_pool(pool_size=2, mock_connect=None)
        # Manually test eager_create
        cfg = MagicMock(spec=ConnectionConfig)
        cfg.connect.side_effect = lambda: MagicMock(name="conn")
        pool2 = ConnectionPool(cfg, pool_size=2, eager_create=True)
        assert pool2._created_count == 2
        assert pool2._pool.qsize() == 2
        pool2.close_all()


class TestConnectionPoolGetStats:
    def test_stats_keys(self):
        pool = make_pool()
        stats = pool.get_stats()
        for key in ("pool_size", "created_connections", "available_connections",
                    "in_use_connections", "total_acquired", "total_released"):
            assert key in stats

    def test_stats_initial_values(self):
        pool = make_pool()
        stats = pool.get_stats()
        assert stats["pool_size"] == 3
        assert stats["created_connections"] == 0
        assert stats["total_acquired"] == 0


class TestConnectionPoolGetAndRelease:
    def test_get_creates_new_connection(self):
        pool = make_pool()
        conn = pool.get_connection()
        assert conn is not None
        assert pool._created_count == 1
        assert pool._acquired_count == 1

    def test_release_puts_back_in_pool(self):
        pool = make_pool()
        conn = pool.get_connection()
        pool.release_connection(conn)
        assert pool._released_count == 1
        assert pool._pool.qsize() == 1

    def test_get_reuses_released_connection(self):
        pool = make_pool()
        conn1 = pool.get_connection()
        pool.release_connection(conn1)
        conn2 = pool.get_connection()
        assert conn1 is conn2
        assert pool._created_count == 1  # still only 1 created

    def test_release_unknown_connection_is_noop(self):
        pool = make_pool()
        unknown = MagicMock()
        pool.release_connection(unknown)
        assert pool._released_count == 0

    def test_pool_respects_max_size(self):
        pool = make_pool(pool_size=1)
        conn = pool.get_connection()
        assert pool._created_count == 1
        # Attempting a second get without release should block; verify the counter
        pool.release_connection(conn)
        conn2 = pool.get_connection()
        assert pool._created_count == 1  # no new connection created


class TestConnectionPoolAcquireContextManager:
    def test_acquire_yields_connection(self):
        pool = make_pool()
        with pool.acquire() as conn:
            assert conn is not None
        assert pool._released_count == 1

    def test_acquire_releases_on_exception(self):
        pool = make_pool()
        try:
            with pool.acquire() as conn:
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert pool._released_count == 1


class TestConnectionPoolCloseAll:
    def test_close_all_clears_connections(self):
        pool = make_pool()
        conn = pool.get_connection()
        pool.release_connection(conn)
        pool.close_all()
        assert pool._created_count == 0
        assert len(pool._all_connections) == 0

    def test_context_manager_closes_on_exit(self):
        cfg = MagicMock(spec=ConnectionConfig)
        cfg.connect.side_effect = lambda: MagicMock()
        with ConnectionPool(cfg, pool_size=2) as pool:
            _ = pool.get_connection()
        assert len(pool._all_connections) == 0
