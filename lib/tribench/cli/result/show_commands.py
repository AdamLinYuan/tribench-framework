"""
Result display commands.

Commands for showing and listing experiment results.
"""

import click
import json
from tribench.cli.base import verbose_option
from .utils import get_storage


@click.command(name="show")
@click.argument("experiment_id")
@click.option('--format', 
              type=click.Choice(['table', 'json', 'yaml']),
              default='table',
              help='Output format.')
@click.option('--metrics', help='Comma-separated list of metrics to show.')
@click.option('--runs', is_flag=True, help='Show all runs for this experiment.')
@verbose_option
@click.pass_context
def show(ctx, experiment_id, format, metrics, runs, verbose):
    """Show experiment results.
    
    \b
    Examples:
        tribench res show exp-001
        tribench res show 1 --format json
        tribench res show 1 --runs
        tribench res show exp-001 --metrics "execution_time,cpu_time"
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        # Try to parse as integer ID first, then as name
        try:
            exp_id = int(experiment_id)
            experiment = storage.get_experiment_by_id(exp_id)
        except ValueError:
            experiment = storage.get_experiment_by_name(experiment_id)
        
        if not experiment:
            click.secho(f"✗ Experiment not found: {experiment_id}", fg='red')
            return
        
        if format == 'json':
            # JSON output
            exp_dict = {
                'id': experiment['id'],
                'name': experiment['name'],
                'type': experiment['experiment_type'],
                'dataset': experiment['dataset_name'],
                'tags': experiment['tags'],
                'created_at': experiment['created_at'].isoformat() if experiment.get('created_at') else None,
                'updated_at': experiment['updated_at'].isoformat() if experiment.get('updated_at') else None,
            }
            
            if runs:
                exp_runs = storage.get_experiment_runs(experiment['id'])
                exp_dict['runs'] = [
                    {
                        'id': r['id'],
                        'run_number': r['run_number'],
                        'status': r['status'],
                        'duration_seconds': r['duration_seconds'],
                        'queries_total': r['queries_total'],
                        'queries_succeeded': r['queries_succeeded'],
                        'queries_failed': r['queries_failed'],
                    }
                    for r in exp_runs
                ]
            
            click.echo(json.dumps(exp_dict, indent=2))
        else:
            # Table output
            click.echo("\n" + "=" * 80)
            click.echo(f"Experiment: {experiment['name']} (ID: {experiment['id']})")
            click.echo("=" * 80)
            click.echo(f"Type:       {experiment['experiment_type']}")
            click.echo(f"Dataset:    {experiment.get('dataset_name') or 'N/A'}")
            click.echo(f"Tags:       {', '.join(experiment.get('tags') or []) if experiment.get('tags') else 'None'}")
            click.echo(f"Created:    {experiment['created_at'].strftime('%Y-%m-%d %H:%M:%S') if experiment.get('created_at') else 'N/A'}")
            
            if runs:
                exp_runs = storage.get_experiment_runs(experiment['id'])
                click.echo(f"\nTotal Runs: {len(exp_runs)}")
                click.echo("\n" + "-" * 100)
                click.echo(f"{'Run':<6} {'Status':<12} {'Duration(s)':<15} {'Queries':<10} {'Success':<10} {'Failed':<10} {'Monitoring':<12}")
                click.echo("-" * 100)
                
                for r in exp_runs:
                    duration = f"{r['duration_seconds']:.2f}" if r.get('duration_seconds') else "N/A"
                    
                    # Get monitoring metrics count
                    try:
                        monitoring_metrics = storage.get_monitoring_metrics(r['id'], limit=1)
                        # Get total count
                        from tribench.storage.connection import get_db_session
                        from tribench.storage.models import MonitoringMetric
                        with get_db_session() as session:
                            metric_count = session.query(MonitoringMetric).filter(
                                MonitoringMetric.run_id == r['id']
                            ).count()
                        monitoring_info = f"{metric_count} metrics" if metric_count > 0 else "None"
                    except:
                        monitoring_info = "N/A"
                    
                    click.echo(
                        f"{r['run_number']:<6} {r['status']:<12} {duration:<15} "
                        f"{r.get('queries_total') or 0:<10} {r.get('queries_succeeded') or 0:<10} "
                        f"{r.get('queries_failed') or 0:<10} {monitoring_info:<12}"
                    )
                click.echo("-" * 100)
            
            click.echo("=" * 80)
            click.echo(f"\nUse '--runs' to see all runs")
            click.echo(f"Use 'tribench res export {experiment['id']}' to export results")
        
    except Exception as e:
        click.secho(f"✗ Failed to show experiment: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@click.command(name="list")
@click.option('--suite', help='Filter by experiment suite.')
@click.option('--status', 
              type=click.Choice(['success', 'failed', 'timeout']),
              help='Filter by status.')
@click.option('--limit', type=int, default=20, help='Number of results to show.')
@click.option('--sort', 
              type=click.Choice(['date', 'duration', 'name']),
              default='date',
              help='Sort results by field.')
@verbose_option
@click.pass_context
def list_results(ctx, suite, status, limit, sort, verbose):
    """List experiment results.
    
    \b
    Examples:
        tribench res list
        tribench res list --suite tpch-sf1
        tribench res list --status success --limit 10
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        experiments = storage.list_experiments(limit=limit)
        
        if not experiments:
            click.echo("No experiments found in database")
            return
        
        # Display header
        click.echo("\n" + "=" * 100)
        click.echo(f"{'ID':<6} {'Name':<30} {'Type':<15} {'Dataset':<15} {'Created':<20}")
        click.echo("=" * 100)
        
        # Display experiments
        for exp in experiments:
            created = exp['created_at'].strftime("%Y-%m-%d %H:%M:%S") if exp.get('created_at') else "N/A"
            dataset = exp.get('dataset_name') or "N/A"
            exp_type = exp.get('experiment_type') or "N/A"
            click.echo(f"{exp['id']:<6} {exp['name'][:28]:<30} {exp_type[:13]:<15} {dataset[:13]:<15} {created:<20}")
        
        click.echo("=" * 100)
        click.echo(f"\nShowing {len(experiments)} experiments")
        click.echo("Use 'tribench res show <id>' to view details")
        
    except Exception as e:
        click.secho(f"✗ Failed to list experiments: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
