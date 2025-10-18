"""Base CLI setup for TriBench using Click."""

import click
import sys
from pathlib import Path
from tribench.__version__ import __version__


# Common options that can be reused across commands
def dry_run_option(f):
    """Decorator for adding --dry-run option."""
    return click.option(
        '--dry-run',
        is_flag=True,
        help='Show what would be done without executing.'
    )(f)


def verbose_option(f):
    """Decorator for adding --verbose option."""
    return click.option(
        '-v', '--verbose',
        is_flag=True,
        help='Enable verbose output.'
    )(f)


def config_option(f):
    """Decorator for adding --config option."""
    return click.option(
        '-c', '--config',
        type=click.Path(exists=True),
        help='Path to configuration file.'
    )(f)


class TriBenchContext:
    """Context object for passing state between commands."""
    
    def __init__(self):
        self.verbose = False
        self.dry_run = False
        self.config_path = None
        self.root_dir = Path(__file__).parent.parent.parent.parent


@click.group()
@click.version_option(version=__version__, prog_name="TriBench")
@verbose_option
@click.pass_context
def cli(ctx, verbose):
    """
    TriBench - Trino Benchmarking Framework
    
    A systematic, reproducible framework for benchmarking SQL workloads
    on distributed data lakehouses using Apache Trino.
    
    \b
    Examples:
        tribench sys setup trino
        tribench exp run experiments/tpch-sf1.yaml
        tribench res show exp-001
    """
    ctx.ensure_object(TriBenchContext)
    ctx.obj.verbose = verbose
    
    if verbose:
        click.echo(f"TriBench v{__version__}", err=True)


@cli.command()
def version():
    """Show detailed version information."""
    click.echo(f"TriBench version {__version__}")
    click.echo("A PEEL-inspired benchmarking framework for Trino")
    click.echo(f"Python: {sys.version.split()[0]}")
    click.echo(f"Platform: {sys.platform}")


if __name__ == "__main__":
    cli()