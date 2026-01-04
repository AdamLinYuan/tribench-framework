"""
Result command package.

Provides CLI commands for viewing and analyzing experiment results.
"""

from .show_commands import show, list_results
from .export_commands import export, compare
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
    'list_results',
    'export',
    'compare',
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
