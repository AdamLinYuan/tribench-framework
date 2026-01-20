"""
Result export and comparison commands.

Commands for exporting results and basic comparisons.
"""

import click
import json
from pathlib import Path
from tribench.cli.base import dry_run_option, verbose_option
from .utils import get_storage


@click.command(name="summary")
@click.argument("experiment_ids", nargs=-1, required=True)
@click.option('--metrics', help='Metrics to compare (comma-separated).')
@click.option('--output', type=click.Path(), help='Save comparison to file.')
@verbose_option
@click.pass_context
def compare(ctx, experiment_ids, metrics, output, verbose):
    """Generate comparison summary for multiple experiments.
    
    Shows side-by-side statistics for quick comparison.
    For statistical analysis, use 'tribench res analyze compare'.
    
    \b
    Examples:
        tribench res summary exp-001 exp-002
        tribench res summary 1 2 3
        tribench res summary 1 2 --metrics execution_time
        tribench res summary 1 2 --output comparison.json
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        if len(experiment_ids) < 2:
            click.secho("✗ Need at least 2 experiments to compare", fg='red')
            return
        
        # Load all experiments
        experiments = []
        for exp_id in experiment_ids:
            try:
                exp_id_int = int(exp_id)
                exp = storage.get_experiment_by_id(exp_id_int)
            except ValueError:
                exp = storage.get_experiment_by_name(exp_id)
            
            if not exp:
                click.secho(f"✗ Experiment not found: {exp_id}", fg='red')
                return
            
            experiments.append(exp)
        
        # Collect statistics for each experiment
        comparison_data = []
        
        for exp in experiments:
            runs = storage.get_experiment_runs(exp.id)
            
            if not runs:
                click.secho(f"⚠ No runs for experiment: {exp.name}", fg='yellow')
                continue
            
            # Aggregate metrics across all runs
            total_queries = 0
            total_execution_time = 0
            succeeded = 0
            failed = 0
            
            for run in runs:
                query_execs = storage.get_run_query_executions(run['id'])
                
                for qe in query_execs:
                    total_queries += 1
                    if qe['execution_time']:
                        total_execution_time += qe['execution_time']
                    
                    if qe['status'] == 'completed':
                        succeeded += 1
                    else:
                        failed += 1
            
            avg_execution_time = total_execution_time / total_queries if total_queries > 0 else 0
            
            comparison_data.append({
                'experiment_id': exp.id,
                'experiment_name': exp.name,
                'total_runs': len(runs),
                'total_queries': total_queries,
                'queries_succeeded': succeeded,
                'queries_failed': failed,
                'avg_execution_time_ms': round(avg_execution_time, 2),
                'success_rate': round(succeeded / total_queries * 100, 2) if total_queries > 0 else 0,
            })
        
        # Output results
        if output:
            with open(output, 'w') as f:
                json.dump({'comparison': comparison_data}, f, indent=2)
            click.secho(f"✓ Comparison saved to {output}", fg='green')
        else:
            # Display table
            click.echo("\n" + "=" * 120)
            click.echo("Experiment Comparison")
            click.echo("=" * 120)
            click.echo(
                f"{'ID':<6} {'Name':<25} {'Runs':<8} {'Queries':<10} "
                f"{'Success':<10} {'Failed':<10} {'Avg Time(ms)':<15} {'Success %':<12}"
            )
            click.echo("=" * 120)
            
            for data in comparison_data:
                click.echo(
                    f"{data['experiment_id']:<6} {data['experiment_name'][:23]:<25} "
                    f"{data['total_runs']:<8} {data['total_queries']:<10} "
                    f"{data['queries_succeeded']:<10} {data['queries_failed']:<10} "
                    f"{data['avg_execution_time_ms']:<15.2f} {data['success_rate']:<12.2f}"
                )
            
            click.echo("=" * 120)
        
    except Exception as e:
        click.secho(f"✗ Failed to compare experiments: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@click.command(name="export")
@click.argument("experiment_id")
@click.option('--format',
              type=click.Choice(['csv', 'json', 'parquet']),
              default='csv',
              help='Export format.')
@click.option('--output', type=click.Path(), help='Output file path.')
@click.option('--include-config', is_flag=True, help='Include experiment configuration.')
@dry_run_option
@verbose_option
@click.pass_context
def export(ctx, experiment_id, format, output, include_config, dry_run, verbose):
    """Export experiment results.
    
    \b
    Examples:
        tribench res export exp-001
        tribench res export 1 --format json --output results.json
        tribench res export 1 --format parquet --include-config
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        # Get experiment
        try:
            exp_id = int(experiment_id)
            experiment = storage.get_experiment_by_id(exp_id)
        except ValueError:
            experiment = storage.get_experiment_by_name(experiment_id)
        
        if not experiment:
            click.secho(f"✗ Experiment not found: {experiment_id}", fg='red')
            return
        
        # Default output filename
        if not output:
            output = f"{experiment['name']}_results.{format}"
        
        if ctx.obj.dry_run:
            click.echo(f"[DRY RUN] Would export {experiment['name']} to {output}")
            return
        
        # Get all runs and query executions
        runs = storage.get_experiment_runs(experiment['id'])
        
        if not runs:
            click.secho(f"✗ No runs found for experiment: {experiment['name']}", fg='yellow')
            return
        
        # Collect all query executions
        all_data = []
        for run in runs:
            query_executions = storage.get_run_query_executions(run['id'])
            
            for qe in query_executions:
                row = {
                    'experiment_id': experiment['id'],
                    'experiment_name': experiment['name'],
                    'run_id': run['id'],
                    'run_number': run['run_number'],
                    'query_name': qe['query_name'],
                    'execution_time_ms': qe['execution_time'],
                    'status': qe['status'],
                    'query_id': qe['query_id'],
                    'input_rows': qe['input_rows'],
                    'input_bytes': qe['input_bytes'],
                    'cpu_time_ms': qe['cpu_time_ms'],
                    'peak_memory_bytes': qe['peak_memory_bytes'],
                    # Advanced query metrics
                    'planning_time_ms': qe.get('planning_time_ms'),
                    'analysis_time_ms': qe.get('analysis_time_ms'),
                    'spilled_bytes': qe.get('spilled_bytes'),
                    'total_splits': qe.get('total_splits'),
                    'completed_splits': qe.get('completed_splits'),
                    'total_tasks': qe.get('total_tasks'),
                    'query_plan_hash': qe.get('query_plan_hash'),
                }
                all_data.append(row)
        
        # Export based on format
        if format == 'json':
            export_data = {
                'experiment': {
                    'id': experiment['id'],
                    'name': experiment['name'],
                    'type': experiment['experiment_type'],
                    'dataset': experiment['dataset_name'],
                },
                'runs': len(runs),
                'query_executions': all_data,
            }
            
            if include_config and experiment.get('config'):
                export_data['config'] = experiment['config']
            
            with open(output, 'w') as f:
                json.dump(export_data, f, indent=2)
            
        elif format == 'csv':
            import csv
            
            if not all_data:
                click.secho("✗ No data to export", fg='yellow')
                return
            
            with open(output, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)
        
        elif format == 'parquet':
            try:
                import pandas as pd
                import pyarrow.parquet as pq
                
                if not all_data:
                    click.secho("✗ No data to export", fg='yellow')
                    return
                
                df = pd.DataFrame(all_data)
                df.to_parquet(output, index=False)
                
            except ImportError:
                click.secho("✗ Parquet export requires pandas and pyarrow", fg='red')
                click.echo("Install with: pip install pandas pyarrow")
                return
        
        click.secho(f"✓ Exported {len(all_data)} query executions to {output}", fg='green')
        
    except Exception as e:
        click.secho(f"✗ Failed to export: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
