"""
Unit tests for monitoring base classes.

Tests MetricCollector, Metric, MonitoringConfig, and MonitoringSession.
"""

import pytest
import time
from datetime import datetime
from pathlib import Path
from tribench.monitoring.base import (
    MetricCollector,
    Metric,
    MonitoringConfig,
    MonitoringSession,
)


class DummyCollector(MetricCollector):
    """Dummy collector for testing."""
    
    def __init__(self):
        super().__init__()
        self.collect_count = 0
    
    def collect(self):
        """Collect dummy metrics."""
        self.collect_count += 1
        return [
            Metric(
                timestamp=datetime.now(),
                type="gauge",
                name="dummy.metric",
                value=42.0,
                unit="count",
                labels={"source": "test"},
            )
        ]


class TestMetric:
    """Test Metric dataclass."""
    
    def test_metric_creation(self):
        """Test creating a metric."""
        metric = Metric(
            timestamp=datetime.now(),
            type="gauge",
            name="test.metric",
            value=100.0,
            unit="bytes",
            labels={"host": "localhost"},
        )
        
        assert metric.name == "test.metric"
        assert metric.value == 100.0
        assert metric.unit == "bytes"
        assert metric.labels["host"] == "localhost"
    
    def test_metric_to_dict(self):
        """Test metric serialization."""
        now = datetime.now()
        metric = Metric(
            timestamp=now,
            type="counter",
            name="test.counter",
            value=5.0,
            unit="count",
            labels={},
        )
        
        data = metric.to_dict()
        
        assert data["name"] == "test.counter"
        assert data["value"] == 5.0
        assert data["type"] == "counter"
        assert "timestamp" in data


class TestMonitoringConfig:
    """Test MonitoringConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MonitoringConfig()
        
        assert config.enabled is True
        assert config.interval == 1.0
        assert config.buffer_size == 1000
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = MonitoringConfig(
            enabled=False,
            interval=2.0,
            storage_path=Path("/tmp/metrics"),
        )
        
        assert config.enabled is False
        assert config.interval == 2.0
        assert config.storage_path == Path("/tmp/metrics")


class TestMetricCollector:
    """Test MetricCollector base class."""
    
    def test_collector_lifecycle(self):
        """Test collector start/stop lifecycle."""
        collector = DummyCollector()
        
        assert not collector.is_running
        
        collector.start()
        assert collector.is_running
        
        collector.stop()
        assert not collector.is_running
    
    def test_collector_collect(self):
        """Test metric collection."""
        collector = DummyCollector()
        collector.start()
        
        metrics = collector.collect()
        
        assert len(metrics) == 1
        assert metrics[0].name == "dummy.metric"
        assert metrics[0].value == 42.0
        assert collector.collect_count == 1
        
        collector.stop()
    
    def test_collector_multiple_collections(self):
        """Test multiple collections."""
        collector = DummyCollector()
        collector.start()
        
        for i in range(5):
            metrics = collector.collect()
            assert len(metrics) == 1
        
        assert collector.collect_count == 5
        
        collector.stop()


class TestMonitoringSession:
    """Test MonitoringSession."""
    
    def test_session_creation(self):
        """Test creating a monitoring session."""
        config = MonitoringConfig(enabled=True, interval=1.0)
        collector = DummyCollector()
        
        session = MonitoringSession(
            config=config,
            collectors=[collector],
            experiment_name="test_experiment",
        )
        
        assert session.experiment_name == "test_experiment"
        assert len(session.collectors) == 1
        assert not session.is_running
    
    def test_session_start_stop(self):
        """Test session lifecycle."""
        config = MonitoringConfig(enabled=True, interval=0.1)
        collector = DummyCollector()
        
        session = MonitoringSession(
            config=config,
            collectors=[collector],
            experiment_name="test",
        )
        
        session.start()
        assert session.is_running
        assert collector.is_running
        
        time.sleep(0.3)  # Let it collect a few times
        
        session.stop()
        assert not session.is_running
        assert not collector.is_running
        
        # Check that metrics were collected
        metrics = session.get_metrics()
        assert len(metrics) > 0
    
    def test_session_multiple_collectors(self):
        """Test session with multiple collectors."""
        config = MonitoringConfig(enabled=True, interval=0.1)
        collector1 = DummyCollector()
        collector2 = DummyCollector()
        
        session = MonitoringSession(
            config=config,
            collectors=[collector1, collector2],
            experiment_name="test",
        )
        
        session.start()
        time.sleep(0.3)
        session.stop()
        
        # Both collectors should have collected
        assert collector1.collect_count > 0
        assert collector2.collect_count > 0
        
        # Should have metrics from both
        metrics = session.get_metrics()
        assert len(metrics) > 0
    
    def test_session_get_summary(self):
        """Test session summary generation."""
        config = MonitoringConfig(enabled=True, interval=0.1)
        collector = DummyCollector()
        
        session = MonitoringSession(
            config=config,
            collectors=[collector],
            experiment_name="test",
        )
        
        session.start()
        time.sleep(0.3)
        session.stop()
        
        summary = session.get_summary()
        
        assert "total_metrics" in summary
        assert "duration_seconds" in summary
        assert summary["total_metrics"] > 0
        assert summary["duration_seconds"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
