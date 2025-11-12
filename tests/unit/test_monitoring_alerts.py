"""
Unit tests for alert system.

Tests AlertManager, AlertThreshold, and alert helper functions.
"""

import pytest
from datetime import datetime
from tribench.monitoring.alerts import (
    AlertManager,
    AlertThreshold,
    Alert,
    AlertSeverity,
    ThresholdCondition,
    create_memory_alert,
    create_cpu_alert,
)
from tribench.monitoring.base import Metric


class TestAlertThreshold:
    """Test AlertThreshold class."""
    
    def test_threshold_creation(self):
        """Test creating a threshold."""
        threshold = AlertThreshold(
            name="test_threshold",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
            severity=AlertSeverity.WARNING,
        )
        
        assert threshold.name == "test_threshold"
        assert threshold.value == 100.0
        assert threshold.enabled
    
    def test_threshold_check_greater_than(self):
        """Test greater than condition."""
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
        )
        
        assert threshold.check(150.0)  # 150 > 100
        assert not threshold.check(100.0)  # 100 not > 100
        assert not threshold.check(50.0)  # 50 not > 100
    
    def test_threshold_check_less_than(self):
        """Test less than condition."""
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.LESS_THAN,
            value=100.0,
        )
        
        assert threshold.check(50.0)  # 50 < 100
        assert not threshold.check(100.0)  # 100 not < 100
        assert not threshold.check(150.0)  # 150 not < 100
    
    def test_threshold_consecutive_violations(self):
        """Test consecutive violations before alert."""
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
            consecutive_violations=3,
        )
        
        # First violation
        assert threshold.check(150.0)
        assert not threshold.should_alert(True)
        
        # Second violation
        assert not threshold.should_alert(True)
        
        # Third violation - should alert
        assert threshold.should_alert(True)
    
    def test_threshold_cooldown(self):
        """Test cooldown period between alerts."""
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
            consecutive_violations=1,
            cooldown_seconds=60,
        )
        
        # First alert
        assert threshold.should_alert(True)
        
        # Immediate second alert - should be blocked by cooldown
        assert not threshold.should_alert(True)


class TestAlertManager:
    """Test AlertManager class."""
    
    def test_manager_creation(self):
        """Test creating alert manager."""
        manager = AlertManager()
        
        assert len(manager.thresholds) == 0
        assert len(manager.alerts) == 0
        assert len(manager.handlers) > 0  # Default handler
    
    def test_add_threshold(self):
        """Test adding thresholds."""
        manager = AlertManager()
        
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
        )
        
        manager.add_threshold(threshold)
        
        assert "test" in manager.thresholds
    
    def test_check_metric_no_violation(self):
        """Test checking metric that doesn't violate threshold."""
        manager = AlertManager()
        
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
            consecutive_violations=1,
        )
        manager.add_threshold(threshold)
        
        metric = Metric(
            timestamp=datetime.now(),
            type="gauge",
            name="test.metric",
            value=50.0,
            unit="count",
            labels={},
        )
        
        alert = manager.check_metric(metric)
        
        assert alert is None
        assert len(manager.alerts) == 0
    
    def test_check_metric_with_violation(self):
        """Test checking metric that violates threshold."""
        manager = AlertManager()
        
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
            consecutive_violations=1,
        )
        manager.add_threshold(threshold)
        
        metric = Metric(
            timestamp=datetime.now(),
            type="gauge",
            name="test.metric",
            value=150.0,
            unit="count",
            labels={},
        )
        
        alert = manager.check_metric(metric)
        
        assert alert is not None
        assert alert.threshold_name == "test"
        assert alert.current_value == 150.0
        assert len(manager.alerts) == 1
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        
        # Create and fire alerts
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
            consecutive_violations=1,
        )
        manager.add_threshold(threshold)
        
        metric = Metric(
            datetime.now(), "gauge", "test.metric", 150.0, "count", {}
        )
        
        manager.check_metric(metric)
        
        # Should have one active alert
        active = manager.get_active_alerts()
        assert len(active) == 1
        
        # Acknowledge alert
        manager.acknowledge_alert(active[0])
        
        # Should have no active alerts
        active = manager.get_active_alerts()
        assert len(active) == 0
    
    def test_alert_handler(self):
        """Test custom alert handler."""
        manager = AlertManager()
        
        # Track handler calls
        handler_called = []
        
        def custom_handler(alert: Alert):
            handler_called.append(alert)
        
        manager.add_handler(custom_handler)
        
        # Create threshold and trigger alert
        threshold = AlertThreshold(
            name="test",
            metric_name="test.metric",
            condition=ThresholdCondition.GREATER_THAN,
            value=100.0,
            consecutive_violations=1,
        )
        manager.add_threshold(threshold)
        
        metric = Metric(
            datetime.now(), "gauge", "test.metric", 150.0, "count", {}
        )
        manager.check_metric(metric)
        
        # Handler should have been called
        assert len(handler_called) == 1
        assert handler_called[0].threshold_name == "test"


class TestAlertHelpers:
    """Test alert helper functions."""
    
    def test_create_memory_alert(self):
        """Test creating memory alert."""
        alert = create_memory_alert(threshold_percent=90.0)
        
        assert alert.name == "high_memory_usage"
        assert alert.metric_name == "system.memory.percent"
        assert alert.value == 90.0
        assert alert.severity == AlertSeverity.WARNING
    
    def test_create_cpu_alert(self):
        """Test creating CPU alert."""
        alert = create_cpu_alert(threshold_percent=95.0)
        
        assert alert.name == "high_cpu_usage"
        assert alert.metric_name == "system.cpu.percent"
        assert alert.value == 95.0
        assert alert.severity == AlertSeverity.WARNING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
