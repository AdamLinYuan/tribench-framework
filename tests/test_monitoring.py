"""Tests for monitoring base classes: MonitoringConfig, Metric, MonitoringSession."""

import time
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from tribench.monitoring.base import (
    Metric,
    MetricType,
    MetricCollector,
    MonitoringConfig,
    MonitoringSession,
)
from tribench.defaults import Defaults


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _FakeCollector(MetricCollector):
    """A concrete MetricCollector that records how many times collect() was called."""

    def __init__(self, config, metrics=None, fail_on_start=False, fail_on_stop=False):
        super().__init__(config)
        self._predefined = metrics or []
        self._fail_on_start = fail_on_start
        self._fail_on_stop = fail_on_stop
        self.collect_count = 0
        self.started = False
        self.stopped = False

    def collect(self):
        self.collect_count += 1
        return list(self._predefined)

    def start(self):
        if self._fail_on_start:
            raise RuntimeError("start failure")
        self.started = True

    def stop(self):
        if self._fail_on_stop:
            raise RuntimeError("stop failure")
        self.stopped = True


@pytest.fixture
def default_config():
    return MonitoringConfig()


@pytest.fixture
def sample_metric():
    return Metric(
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
        metric_type=MetricType.SYSTEM_RESOURCE,
        name="cpu_percent",
        value=42.5,
        unit="%",
        labels={"core": "0"},
    )


# ---------------------------------------------------------------------------
# MonitoringConfig
# ---------------------------------------------------------------------------

class TestMonitoringConfig:
    def test_defaults(self, default_config):
        assert default_config.enabled is True
        assert default_config.interval_seconds == 1.0
        assert default_config.collect_system_resources is True
        assert default_config.collect_trino_jmx is True
        assert default_config.buffer_size == 1000

    def test_custom_values(self):
        cfg = MonitoringConfig(enabled=False, interval_seconds=5.0)
        assert cfg.enabled is False
        assert cfg.interval_seconds == 5.0


# ---------------------------------------------------------------------------
# Metric
# ---------------------------------------------------------------------------

class TestMetric:
    def test_to_dict_keys(self, sample_metric):
        d = sample_metric.to_dict()
        for key in ("timestamp", "metric_type", "name", "value", "unit", "labels"):
            assert key in d

    def test_to_dict_timestamp_isoformat(self, sample_metric):
        d = sample_metric.to_dict()
        assert d["timestamp"] == "2025-01-01T12:00:00"

    def test_to_dict_metric_type_is_string(self, sample_metric):
        d = sample_metric.to_dict()
        assert isinstance(d["metric_type"], str)
        assert d["metric_type"] == "system_resource"

    def test_to_dict_value_and_unit(self, sample_metric):
        d = sample_metric.to_dict()
        assert d["value"] == 42.5
        assert d["unit"] == "%"

    def test_to_dict_labels(self, sample_metric):
        d = sample_metric.to_dict()
        assert d["labels"] == {"core": "0"}

    def test_empty_labels_default(self, default_config):
        m = Metric(
            timestamp=datetime.now(),
            metric_type=MetricType.CUSTOM,
            name="test",
            value=1,
            unit="",
        )
        assert m.labels == {}


# ---------------------------------------------------------------------------
# MetricCollector (via FakeCollector)
# ---------------------------------------------------------------------------

class TestMetricCollector:
    def test_is_enabled_when_both_enabled(self, default_config):
        collector = _FakeCollector(default_config)
        assert collector.is_enabled() is True

    def test_is_disabled_when_collector_disabled(self, default_config):
        collector = _FakeCollector(default_config)
        collector.enabled = False
        assert collector.is_enabled() is False

    def test_is_disabled_when_config_disabled(self):
        cfg = MonitoringConfig(enabled=False)
        collector = _FakeCollector(cfg)
        assert collector.is_enabled() is False

    def test_buffer_metrics(self, default_config, sample_metric):
        collector = _FakeCollector(default_config)
        collector.buffer_metrics([sample_metric])
        assert len(collector._metrics_buffer) == 1

    def test_flush_buffer_returns_and_clears(self, default_config, sample_metric):
        collector = _FakeCollector(default_config)
        collector.buffer_metrics([sample_metric, sample_metric])
        flushed = collector.flush_buffer()
        assert len(flushed) == 2
        assert len(collector._metrics_buffer) == 0


# ---------------------------------------------------------------------------
# MonitoringSession
# ---------------------------------------------------------------------------

class TestMonitoringSessionInit:
    def test_initial_state(self, default_config):
        session = MonitoringSession(default_config, "exp-1")
        assert session.is_running is False
        assert session.start_time is None
        assert session.end_time is None
        assert session.collectors == []

    def test_add_collector(self, default_config):
        session = MonitoringSession(default_config, "exp-1")
        c = _FakeCollector(default_config)
        session.add_collector(c)
        assert len(session.collectors) == 1

    def test_init_with_collectors(self, default_config):
        c = _FakeCollector(default_config)
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        assert len(session.collectors) == 1


class TestMonitoringSessionStartStop:
    def test_start_sets_running(self, default_config):
        session = MonitoringSession(default_config, "exp-1")
        session.start()
        assert session.is_running is True
        assert session.start_time is not None
        session.stop()

    def test_stop_sets_not_running(self, default_config):
        session = MonitoringSession(default_config, "exp-1")
        session.start()
        session.stop()
        assert session.is_running is False
        assert session.end_time is not None

    def test_start_twice_is_noop(self, default_config):
        session = MonitoringSession(default_config, "exp-1")
        session.start()
        first_start_time = session.start_time
        session.start()  # second call should do nothing
        assert session.start_time == first_start_time
        session.stop()

    def test_stop_not_started_is_noop(self, default_config):
        session = MonitoringSession(default_config, "exp-1")
        session.stop()  # Should not raise

    def test_start_calls_collector_start(self, default_config):
        c = _FakeCollector(default_config)
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        session.start()
        assert c.started is True
        session.stop()

    def test_stop_calls_collector_stop(self, default_config):
        c = _FakeCollector(default_config)
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        session.start()
        session.stop()
        assert c.stopped is True

    def test_collector_start_failure_does_not_crash_session(self, default_config):
        c = _FakeCollector(default_config, fail_on_start=True)
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        session.start()  # should not raise
        assert session.is_running is True
        session.stop()

    def test_collector_stop_failure_does_not_crash_session(self, default_config):
        c = _FakeCollector(default_config, fail_on_stop=True)
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        session.start()
        session.stop()  # should not raise


class TestMonitoringSessionCollect:
    def test_collect_metrics_returns_from_collectors(self, default_config, sample_metric):
        c = _FakeCollector(default_config, metrics=[sample_metric])
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        metrics = session.collect_metrics()
        assert len(metrics) == 1
        assert metrics[0] is sample_metric

    def test_collect_from_disabled_collector_skipped(self, default_config, sample_metric):
        c = _FakeCollector(default_config, metrics=[sample_metric])
        c.enabled = False
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        metrics = session.collect_metrics()
        assert metrics == []

    def test_collector_exception_does_not_crash_session(self, default_config):
        c = MagicMock(spec=MetricCollector)
        c.is_enabled.return_value = True
        c.collect.side_effect = RuntimeError("boom")
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        metrics = session.collect_metrics()
        assert metrics == []


class TestMonitoringSessionSummary:
    def test_summary_keys(self, default_config):
        session = MonitoringSession(default_config, "my-exp")
        summary = session.get_summary()
        for key in ("experiment_name", "start_time", "end_time",
                    "duration_seconds", "collectors_count", "is_running"):
            assert key in summary

    def test_summary_experiment_name(self, default_config):
        session = MonitoringSession(default_config, "named-exp")
        assert session.get_summary()["experiment_name"] == "named-exp"

    def test_summary_duration_after_stop(self, default_config):
        session = MonitoringSession(default_config, "dur-exp")
        session.start()
        time.sleep(0.05)
        session.stop()
        summary = session.get_summary()
        assert summary["duration_seconds"] is not None
        assert summary["duration_seconds"] >= 0.0

    def test_summary_collectors_list(self, default_config):
        c = _FakeCollector(default_config)
        session = MonitoringSession(default_config, "exp-1", collectors=[c])
        summary = session.get_summary()
        assert "_FakeCollector" in summary["collectors"]
