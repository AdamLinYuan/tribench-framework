"""
DEPRECATED: This module is deprecated. Use tribench.cli.system instead.

Backwards compatibility wrapper for system commands.
"""

import warnings
import click
from tribench.cli.base import cli

# Import from new locations
from tribench.cli.system import (
    setup,
    start,
    stop,
    teardown,
    status,
    logs,
    port_forward,
    cluster,
)

# Deprecated import warning
warnings.warn(
    "tribench.cli.system_commands is deprecated. "
    "Use tribench.cli.system instead.",
    DeprecationWarning,
    stacklevel=2
)

# Register system group with subcommands
@cli.group(name="sys")
def system_group():
    """System lifecycle management commands.
    
    Manage Trino, PostgreSQL, MinIO and other system components.
    """
    pass

# Register commands
system_group.add_command(setup)
system_group.add_command(start)
system_group.add_command(stop)
system_group.add_command(teardown)
system_group.add_command(status)
system_group.add_command(logs)
system_group.add_command(port_forward)
system_group.add_command(cluster)

__all__ = ['system_group']
