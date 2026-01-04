"""Dataset management commands.

This module maintains backwards compatibility by importing commands from the new modular structure.
"""

import click
from tribench.cli.base import cli
from tribench.cli.data import (
    generate,
    load,
    load_iceberg,
    list_datasets,
    info,
    validate,
    validate_iceberg
)


@cli.group(name="data")
def data_group():
    """Dataset management commands.
    
    Generate, load and manage benchmark datasets.
    """
    pass


# Register all commands with the data group
data_group.add_command(generate)
data_group.add_command(load)
data_group.add_command(load_iceberg)
data_group.add_command(list_datasets)
data_group.add_command(info)
data_group.add_command(validate)
data_group.add_command(validate_iceberg)


# Backwards compatibility exports
__all__ = [
    'data_group',
    'generate',
    'load',
    'load_iceberg',
    'list_datasets',
    'info',
    'validate',
    'validate_iceberg'
]
