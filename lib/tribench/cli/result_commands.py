"""
DEPRECATED: This module is deprecated. Use tribench.cli.result instead.

Backwards compatibility wrapper for result commands.
"""

import warnings
import click
from tribench.cli.base import cli

# Import from new locations
from tribench.cli.result import (
    show,
    show_queries,
    list_results,
    export,
    summary,
    analyze_group,
    delete,
    archive,
    show_monitoring,
    reset_database,
)

# Deprecated import warning
warnings.warn(
    "tribench.cli.result_commands is deprecated. "
    "Use tribench.cli.result instead.",
    DeprecationWarning,
    stacklevel=2
)

# Register result group with subcommands
@cli.group(name="res")
def result_group():
    """Result viewing and basic analysis commands.
    
    View, analyze and export experiment results.
    """
    pass

# Register commands
result_group.add_command(show)
result_group.add_command(show_queries)
result_group.add_command(list_results)
result_group.add_command(summary)
result_group.add_command(export)
result_group.add_command(analyze_group)
result_group.add_command(delete)
result_group.add_command(archive)
result_group.add_command(show_monitoring)
result_group.add_command(reset_database)

__all__ = ['result_group']
