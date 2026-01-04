"""Suite information and query commands."""

import click
import sys
from pathlib import Path

from tribench.cli.base import verbose_option
from tribench.core.experiment_suite import ExperimentSuite


@click.command(name="list")
@click.option('--path', type=click.Path(exists=True), 
              default='experiments/suites',
              help='Directory to search for suites.')
@verbose_option
@click.pass_context
def list_suites(ctx, path, verbose):
    """List available experiment suites.
    
    \b
    Examples:
        tribench suite list
        tribench suite list --path experiments/suites
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    suite_dir = Path(path)
    
    if not suite_dir.exists():
        click.secho(f"✗ Directory not found: {suite_dir}", fg='red')
        return
    
    # Find all YAML files in suite directory
    suite_files = list(suite_dir.glob('*.yaml')) + list(suite_dir.glob('*.yml'))
    
    if not suite_files:
        click.echo(f"No suite files found in {suite_dir}")
        return
    
    click.echo(f"Available suites in {suite_dir}:\n")
    
    for suite_file in sorted(suite_files):
        try:
            suite = ExperimentSuite.from_yaml(suite_file)
            click.echo(f"  {suite.name}")
            if suite.description:
                click.echo(f"    {suite.description}")
            click.echo(f"    Experiments: {len(suite.experiments)}")
            click.echo(f"    File: {suite_file.name}")
            if ctx.obj.verbose and suite.default_config:
                click.echo(f"    Defaults: {list(suite.default_config.keys())}")
            click.echo()
        except Exception as e:
            click.secho(f"  ✗ {suite_file.name}: {e}", fg='yellow')


@click.command(name="show")
@click.argument("suite", type=click.Path(exists=True))
@verbose_option
@click.pass_context
def show_suite(ctx, suite, verbose):
    """Show detailed information about a suite.
    
    \b
    Examples:
        tribench suite show experiments/suites/tpch-suite.yaml
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    suite_path = Path(suite)
    
    try:
        exp_suite = ExperimentSuite.from_yaml(suite_path)
        
        click.echo(f"Suite: {exp_suite.name}")
        click.echo(f"{'='*60}")
        
        if exp_suite.description:
            click.echo(f"\nDescription:")
            click.echo(f"  {exp_suite.description}")
        
        if exp_suite.default_config:
            click.echo(f"\nSuite Defaults:")
            import json
            click.echo(json.dumps(exp_suite.default_config, indent=2))
        
        click.echo(f"\nExperiments ({len(exp_suite.experiments)}):")
        for i, exp in enumerate(exp_suite.experiments, 1):
            click.echo(f"\n  {i}. {exp.name}")
            click.echo(f"     System: {exp.system}")
            click.echo(f"     Runs: {exp.runs}")
            if exp.warmup_runs > 0:
                click.echo(f"     Warmup runs: {exp.warmup_runs}")
            click.echo(f"     Timeout: {exp.timeout_seconds}s")
            if exp.dataset:
                click.echo(f"     Dataset: {exp.dataset}")
            
            query_count = len(exp.queries) + len(exp.query_files)
            click.echo(f"     Queries: {query_count}")
            
            if ctx.obj.verbose:
                if exp.validation:
                    click.echo(f"     Validation: {exp.validation}")
                if exp.metadata:
                    click.echo(f"     Metadata: {exp.metadata}")
        
    except Exception as e:
        click.secho(f"✗ Error: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)
