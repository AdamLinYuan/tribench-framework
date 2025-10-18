"""CLI module for TriBench."""

from tribench.cli.base import cli

# Import all command modules to register them with the CLI
from tribench.cli import system_commands
from tribench.cli import experiment_commands
from tribench.cli import data_commands
from tribench.cli import result_commands

__all__ = ["cli"]

