"""Experiment suite execution commands.

This module maintains backwards compatibility by importing commands from the new modular structure.
"""

import click
from tribench.cli.base import cli
from tribench.cli.suite import (
    run_suite,
    list_suites,
    show_suite
)


@cli.group(name="suite")
def suite_group():
    """Experiment suite execution commands.
    
    Run and manage collections of experiments with shared configuration.
    """
    pass


# Register all commands with the suite group
suite_group.add_command(run_suite)
suite_group.add_command(list_suites)
suite_group.add_command(show_suite)


# Backwards compatibility exports
__all__ = [
    'suite_group',
    'run_suite',
    'list_suites',
    'show_suite'
]

