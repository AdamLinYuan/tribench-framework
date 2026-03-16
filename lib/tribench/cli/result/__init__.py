"""
Result command package.

Provides CLI commands for viewing and analyzing experiment results.
"""

from .show_commands import show, list_results, show_queries, suite_summary
from .export_commands import export, compare as summary
from .analysis_commands import (
    analyze_group,
    analyze_statistics,
    analyze_performance,
    analyze_compare,
    analyze_scalability,
    analyze_regression,
)
from .management_commands import delete, archive, show_monitoring, reset_database

__all__ = [
    'show',
    'show_queries',
    'list_results',
    'suite_summary',
    'export',
    'summary',
    'analyze_group',
    'analyze_statistics',
    'analyze_performance',
    'analyze_compare',
    'analyze_scalability',
    'analyze_regression',
    'delete',
    'archive',
    'show_monitoring',
    'reset_database',
]
