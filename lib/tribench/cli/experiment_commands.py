"""Experiment execution commands."""

import click
import sys
import logging
from pathlib import Path
from tribench.cli.base import cli, dry_run_option, verbose_option, config_option
from tribench.core.experiment import ExperimentConfig
from tribench.experiments import TrinoExperiment

logger = logging.getLogger(__name__)


@cli.group(name="exp")
def experiment_group():
    """Experiment execution commands.
    
    Run, monitor and manage benchmark experiments.
    """
    pass


@experiment_group.command(name="run")
@click.argument("experiment", type=click.Path(exists=True))
@click.option('--runs', type=int, help='Override number of runs to execute.')
@click.option('--warmup', type=int, help='Override number of warmup runs.')
@click.option('--timeout', type=int, help='Override timeout in seconds.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def run(ctx, experiment, runs, warmup, timeout, config, dry_run, verbose):
    """Execute an experiment.
    
    \b
    Examples:
        tribench exp run experiments/tpch-sf1.yaml
        tribench exp run experiments/tpch-sf1.yaml --runs 3 --warmup 1
        tribench exp run experiments/test-simple.yaml --timeout 60 --dry-run
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Set up logging level
    if ctx.obj.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    exp_path = Path(experiment)
    
    try:
        # Build CLI overrides dictionary
        cli_overrides = {}
        if runs is not None:
            cli_overrides['runs'] = runs
        if warmup is not None:
            cli_overrides['warmup_runs'] = warmup
        if timeout is not None:
            cli_overrides['timeout_seconds'] = timeout
        
        # Load experiment configuration with CLI overrides
        click.echo(f"Loading experiment: {exp_path.name}")
        exp_config = ExperimentConfig.from_yaml(
            exp_path,
            cli_overrides=cli_overrides if cli_overrides else None
        )
        
        # Display configuration
        click.echo(f"\nExperiment: {exp_config.name}")
        click.echo(f"Description: {exp_config.description}")
        click.echo(f"System: {exp_config.system}")
        click.echo(f"Runs: {exp_config.runs}")
        if exp_config.warmup_runs > 0:
            click.echo(f"Warmup runs: {exp_config.warmup_runs}")
        click.echo(f"Timeout: {exp_config.timeout_seconds}s")
        
        query_count = len(exp_config.queries) + len(exp_config.query_files)
        click.echo(f"Queries: {query_count}")
        
        if ctx.obj.dry_run:
            click.echo(f"\n[DRY RUN] Would execute experiment with above configuration")
            return
        
        # Validate experiment can only run on Trino for now
        if exp_config.system.lower() != "trino":
            click.secho(f"✗ Error: Only 'trino' system is currently supported", fg='red')
            sys.exit(1)
        
        # Create and prepare experiment
        click.echo(f"\nPreparing experiment...")
        experiment = TrinoExperiment(exp_config)
        
        try:
            experiment.prepare()
            click.secho("✓ Preparation complete", fg='green')
        except Exception as e:
            click.secho(f"✗ Preparation failed: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                click.echo(traceback.format_exc())
            sys.exit(1)
        
        # Execute experiment
        click.echo(f"\nExecuting experiment...")
        click.echo("-" * 60)
        
        try:
            results = experiment.run()
            click.echo("-" * 60)
            click.secho("✓ Execution complete", fg='green')
            
            # Display results summary
            click.echo(f"\nResults Summary:")
            click.echo(f"  Duration: {results['total_duration_seconds']:.2f}s")
            click.echo(f"  Runs completed: {results['runs_completed']}/{results['runs_requested']}")
            
            stats = results.get('statistics', {})
            if 'successful_runs' in stats:
                click.echo(f"  Success rate: {stats['success_rate']:.1%}")
            
            if 'execution_time' in stats:
                exec_time = stats['execution_time']
                click.echo(f"  Execution time (mean): {exec_time['mean']:.3f}s")
                click.echo(f"  Execution time (median): {exec_time['median']:.3f}s")
                click.echo(f"  Execution time (stddev): {exec_time['stdev']:.3f}s")
            
            # Validate results
            click.echo(f"\nValidating results...")
            if experiment.validate():
                click.secho("✓ Validation passed", fg='green')
            else:
                click.secho("✗ Validation failed", fg='yellow')
            
        except Exception as e:
            click.echo("-" * 60)
            click.secho(f"✗ Execution failed: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                click.echo(traceback.format_exc())
            sys.exit(1)
        finally:
            # Cleanup
            experiment.cleanup()
        
        click.echo(f"\nResults saved to: results/")
        click.secho(f"\n✓ Experiment '{exp_config.name}' completed successfully", fg='green')
        
    except FileNotFoundError as e:
        click.secho(f"✗ Error: {e}", fg='red')
        sys.exit(1)
    except ValueError as e:
        click.secho(f"✗ Configuration error: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)


@experiment_group.command(name="list")
@click.option('--filter', help='Filter experiments by pattern.')
@click.option('--status', 
              type=click.Choice(['pending', 'running', 'completed', 'failed']),
              help='Filter by experiment status.')
@verbose_option
@click.pass_context
def list_experiments(ctx, filter, status, verbose):
    """List available experiments.
    
    \b
    Examples:
        tribench exp list
        tribench exp list --filter "tpch*"
        tribench exp list --status completed
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        if filter:
            click.echo(f"Filter: {filter}")
        if status:
            click.echo(f"Status: {status}")
    
    # TODO: Implement experiment listing
    click.secho("✗ Experiment listing not yet implemented", fg='yellow')


@experiment_group.command(name="status")
@click.argument("experiment_id")
@click.option('--follow', '-f', is_flag=True, help='Follow experiment progress.')
@verbose_option
@click.pass_context
def exp_status(ctx, experiment_id, follow, verbose):
    """Check experiment status.
    
    \b
    Examples:
        tribench exp status exp-001
        tribench exp status exp-001 --follow
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Experiment ID: {experiment_id}")
        if follow:
            click.echo("Following experiment progress...")
    
    # TODO: Implement experiment status
    click.secho(f"✗ Status check for {experiment_id} not yet implemented", fg='yellow')


@experiment_group.command(name="cancel")
@click.argument("experiment_id")
@click.confirmation_option(prompt='Are you sure you want to cancel this experiment?')
@verbose_option
@click.pass_context
def cancel(ctx, experiment_id, verbose):
    """Cancel a running experiment.
    
    \b
    Examples:
        tribench exp cancel exp-001
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Cancelling experiment: {experiment_id}")
    
    # TODO: Implement experiment cancellation
    click.secho(f"✗ Cancel for {experiment_id} not yet implemented", fg='yellow')


@experiment_group.command(name="config")
@click.argument("experiment", type=click.Path(exists=True))
@click.option('--validate', is_flag=True, help='Validate configuration only.')
@verbose_option
@click.pass_context
def show_config(ctx, experiment, validate, verbose):
    """Show experiment configuration.
    
    \b
    Examples:
        tribench exp config experiments/tpch-sf1.yaml
        tribench exp config experiments/tpch-sf1.yaml --validate
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    exp_path = Path(experiment)
    
    if ctx.obj.verbose:
        click.echo(f"Experiment: {exp_path}")
        if validate:
            click.echo("Validation mode enabled")
    
    # TODO: Implement config display
    click.secho(f"✗ Config display for {exp_path.name} not yet implemented", fg='yellow')
