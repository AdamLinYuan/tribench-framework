"""Trino-specific experiment implementation.

DEPRECATED: This module is maintained for backwards compatibility.
The implementation has been refactored into the tribench.experiments.trino package.

New code should import directly from:
    from tribench.experiments.trino import TrinoExperiment

Or from the package:
    from tribench.experiments import TrinoExperiment
"""

import warnings

# Re-export from new location for backwards compatibility
from .trino import TrinoExperiment
from .trino.monitoring import ExperimentMonitoringMixin, is_monitoring_available
from .trino.storage import ExperimentStorageMixin, is_storage_available
from .trino.parallel import ParallelExecutionMixin

# Issue deprecation warning when this module is imported directly
warnings.warn(
    "tribench.experiments.trino_experiment is deprecated. "
    "Import from tribench.experiments.trino or tribench.experiments instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "TrinoExperiment",
    "ExperimentMonitoringMixin",
    "ExperimentStorageMixin",
    "ParallelExecutionMixin",
    "is_monitoring_available",
    "is_storage_available",
]
