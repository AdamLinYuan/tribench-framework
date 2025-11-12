"""
Alert system for monitoring thresholds.

Provides:
- Threshold-based alerting
- Alert severity levels
- Alert history tracking
- Customizable alert handlers
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable

from .base import Metric

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ThresholdCondition(Enum):
    """Threshold condition types."""
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"


@dataclass
class AlertThreshold:
    """
    Definition of an alert threshold.
    
    Specifies conditions that trigger alerts when metrics
    violate defined thresholds.
    """
    
    # Threshold identification
    name: str
    metric_name: str
    
    # Condition
    condition: ThresholdCondition
    value: float
    
    # Alert properties
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    
    # Threshold behavior
    enabled: bool = True
    cooldown_seconds: int = 60  # Minimum time between alerts
    consecutive_violations: int = 1  # Violations before alerting
    
    # Internal state
    _violation_count: int = field(default=0, init=False, repr=False)
    _last_alert_time: Optional[datetime] = field(default=None, init=False, repr=False)
    
    def check(self, value: float) -> bool:
        """
        Check if value violates threshold.
        
        Args:
            value: Metric value to check
            
        Returns:
            True if threshold is violated
        """
        if not self.enabled:
            return False
        
        condition_map = {
            ThresholdCondition.GREATER_THAN: lambda v: v > self.value,
            ThresholdCondition.LESS_THAN: lambda v: v < self.value,
            ThresholdCondition.EQUALS: lambda v: v == self.value,
            ThresholdCondition.NOT_EQUALS: lambda v: v != self.value,
            ThresholdCondition.GREATER_EQUAL: lambda v: v >= self.value,
            ThresholdCondition.LESS_EQUAL: lambda v: v <= self.value,
        }
        
        return condition_map[self.condition](value)
    
    def should_alert(self, violated: bool) -> bool:
        """
        Determine if alert should be fired based on violation state.
        
        Args:
            violated: Whether threshold is currently violated
            
        Returns:
            True if alert should be fired
        """
        now = datetime.now()
        
        # Check cooldown
        if self._last_alert_time:
            seconds_since_last = (now - self._last_alert_time).total_seconds()
            if seconds_since_last < self.cooldown_seconds:
                return False
        
        # Track consecutive violations
        if violated:
            self._violation_count += 1
        else:
            self._violation_count = 0
            return False
        
        # Fire alert if consecutive violations met
        if self._violation_count >= self.consecutive_violations:
            self._last_alert_time = now
            self._violation_count = 0  # Reset after firing
            return True
        
        return False


@dataclass
class Alert:
    """
    An alert event.
    
    Represents a triggered alert with context and metadata.
    """
    
    timestamp: datetime
    threshold_name: str
    metric_name: str
    severity: AlertSeverity
    message: str
    
    # Context
    current_value: float
    threshold_value: float
    condition: ThresholdCondition
    
    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "threshold_name": self.threshold_name,
            "metric_name": self.metric_name,
            "severity": self.severity.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "condition": self.condition.value,
            "labels": self.labels,
            "acknowledged": self.acknowledged,
        }


# Type alias for alert handlers
AlertHandler = Callable[[Alert], None]


class AlertManager:
    """
    Manages alert thresholds and alert firing.
    
    Monitors metrics against configured thresholds and fires
    alerts when violations occur.
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self.thresholds: Dict[str, AlertThreshold] = {}
        self.alerts: List[Alert] = []
        self.handlers: List[AlertHandler] = []
        
        # Add default handler (logging)
        self.add_handler(self._default_log_handler)
        
        logger.info("AlertManager initialized")
    
    def add_threshold(self, threshold: AlertThreshold) -> None:
        """
        Add an alert threshold.
        
        Args:
            threshold: AlertThreshold to add
        """
        self.thresholds[threshold.name] = threshold
        logger.info(f"Added threshold: {threshold.name} for {threshold.metric_name}")
    
    def remove_threshold(self, name: str) -> None:
        """
        Remove an alert threshold.
        
        Args:
            name: Name of threshold to remove
        """
        if name in self.thresholds:
            del self.thresholds[name]
            logger.info(f"Removed threshold: {name}")
    
    def add_handler(self, handler: AlertHandler) -> None:
        """
        Add an alert handler function.
        
        Handler will be called for each alert fired.
        
        Args:
            handler: Callable that accepts Alert object
        """
        self.handlers.append(handler)
        logger.debug(f"Added alert handler: {handler.__name__}")
    
    def check_metric(self, metric: Metric) -> Optional[Alert]:
        """
        Check a metric against all relevant thresholds.
        
        Args:
            metric: Metric to check
            
        Returns:
            Alert object if threshold violated, None otherwise
        """
        for threshold in self.thresholds.values():
            if not threshold.enabled:
                continue
            
            # Check if this threshold applies to this metric
            if threshold.metric_name != metric.name:
                continue
            
            # Check if threshold is violated
            violated = threshold.check(metric.value)
            
            # Determine if alert should fire
            if threshold.should_alert(violated):
                # Create alert
                alert = Alert(
                    timestamp=metric.timestamp,
                    threshold_name=threshold.name,
                    metric_name=metric.name,
                    severity=threshold.severity,
                    message=threshold.message or self._generate_message(threshold, metric),
                    current_value=metric.value,
                    threshold_value=threshold.value,
                    condition=threshold.condition,
                    labels=metric.labels.copy(),
                )
                
                # Fire alert
                self._fire_alert(alert)
                return alert
        
        return None
    
    def check_metrics(self, metrics: List[Metric]) -> List[Alert]:
        """
        Check multiple metrics against thresholds.
        
        Args:
            metrics: List of metrics to check
            
        Returns:
            List of alerts fired
        """
        alerts = []
        for metric in metrics:
            alert = self.check_metric(metric)
            if alert:
                alerts.append(alert)
        return alerts
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """
        Get active (unacknowledged) alerts.
        
        Args:
            severity: Filter by severity level (optional)
            
        Returns:
            List of active alerts
        """
        alerts = [a for a in self.alerts if not a.acknowledged]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    def acknowledge_alert(self, alert: Alert) -> None:
        """
        Acknowledge an alert.
        
        Args:
            alert: Alert to acknowledge
        """
        alert.acknowledged = True
        logger.info(f"Alert acknowledged: {alert.threshold_name}")
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()
        logger.info("All alerts cleared")
    
    def _fire_alert(self, alert: Alert) -> None:
        """
        Fire an alert (call all handlers).
        
        Args:
            alert: Alert to fire
        """
        # Store alert
        self.alerts.append(alert)
        
        # Call handlers
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler {handler.__name__} failed: {e}")
    
    def _generate_message(self, threshold: AlertThreshold, metric: Metric) -> str:
        """
        Generate default alert message.
        
        Args:
            threshold: Threshold that was violated
            metric: Metric that violated threshold
            
        Returns:
            Alert message string
        """
        condition_str = {
            ThresholdCondition.GREATER_THAN: ">",
            ThresholdCondition.LESS_THAN: "<",
            ThresholdCondition.EQUALS: "==",
            ThresholdCondition.NOT_EQUALS: "!=",
            ThresholdCondition.GREATER_EQUAL: ">=",
            ThresholdCondition.LESS_EQUAL: "<=",
        }[threshold.condition]
        
        return (
            f"{metric.name} {condition_str} {threshold.value} "
            f"(current: {metric.value} {metric.unit})"
        )
    
    @staticmethod
    def _default_log_handler(alert: Alert) -> None:
        """
        Default alert handler that logs to logger.
        
        Args:
            alert: Alert to log
        """
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }[alert.severity]
        
        logger.log(
            log_level,
            f"[ALERT] {alert.severity.value.upper()}: {alert.message}"
        )


# Predefined threshold templates for common scenarios

def create_memory_alert(threshold_percent: float = 90.0) -> AlertThreshold:
    """
    Create memory usage alert threshold.
    
    Args:
        threshold_percent: Memory usage percentage threshold
        
    Returns:
        AlertThreshold for memory usage
    """
    return AlertThreshold(
        name="high_memory_usage",
        metric_name="system.memory.percent",
        condition=ThresholdCondition.GREATER_THAN,
        value=threshold_percent,
        severity=AlertSeverity.WARNING,
        message=f"Memory usage exceeded {threshold_percent}%",
        consecutive_violations=3,
    )


def create_cpu_alert(threshold_percent: float = 95.0) -> AlertThreshold:
    """
    Create CPU usage alert threshold.
    
    Args:
        threshold_percent: CPU usage percentage threshold
        
    Returns:
        AlertThreshold for CPU usage
    """
    return AlertThreshold(
        name="high_cpu_usage",
        metric_name="system.cpu.percent",
        condition=ThresholdCondition.GREATER_THAN,
        value=threshold_percent,
        severity=AlertSeverity.WARNING,
        message=f"CPU usage exceeded {threshold_percent}%",
        consecutive_violations=5,
    )


def create_disk_space_alert(threshold_percent: float = 85.0) -> AlertThreshold:
    """
    Create disk space alert threshold.
    
    Args:
        threshold_percent: Disk usage percentage threshold
        
    Returns:
        AlertThreshold for disk space
    """
    return AlertThreshold(
        name="low_disk_space",
        metric_name="system.disk.percent",
        condition=ThresholdCondition.GREATER_THAN,
        value=threshold_percent,
        severity=AlertSeverity.CRITICAL,
        message=f"Disk space usage exceeded {threshold_percent}%",
        consecutive_violations=2,
    )


def create_query_timeout_alert(threshold_seconds: float = 300.0) -> AlertThreshold:
    """
    Create query timeout alert threshold.
    
    Args:
        threshold_seconds: Query duration threshold in seconds
        
    Returns:
        AlertThreshold for query duration
    """
    return AlertThreshold(
        name="long_running_query",
        metric_name="trino.query.time.elapsed",
        condition=ThresholdCondition.GREATER_THAN,
        value=threshold_seconds * 1000,  # Convert to milliseconds
        severity=AlertSeverity.INFO,
        message=f"Query running longer than {threshold_seconds}s",
        consecutive_violations=1,
        cooldown_seconds=300,
    )
