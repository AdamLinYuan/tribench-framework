"""
DEPRECATED: This module is deprecated. Use tribench.monitoring.trino instead.

Backwards compatibility wrapper for TrinoMonitor.
"""

import warnings

# Import from new location
from tribench.monitoring.trino import TrinoMonitor
from tribench.monitoring.trino.models import QueryMetrics, ClusterMetrics

# Deprecated import warning
warnings.warn(
    "tribench.monitoring.trino_monitor is deprecated. "
    "Use tribench.monitoring.trino instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['TrinoMonitor', 'QueryMetrics', 'ClusterMetrics']
