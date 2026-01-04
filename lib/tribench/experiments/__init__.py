"""Experiment execution engine."""

from .query_executor import QueryExecutor, QueryExecutionError, QueryTimeoutError
from .result_collector import ResultCollector

# Import TrinoExperiment from the new modular package
from .trino import TrinoExperiment

# Backwards compatibility: also expose from old location
# (trino_experiment.py now re-exports from trino/)

__all__ = [
    "QueryExecutor",
    "QueryExecutionError",
    "QueryTimeoutError",
    "ResultCollector",
    "TrinoExperiment",
]
