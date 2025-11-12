"""Result viewing and analysis commands."""

import click
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from tribench.cli.base import cli, dry_run_option, verbose_option

# Import storage components
try:
    from tribench.storage import (
        ResultStorage,
        init_database,
        get_db_session,
    )
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False


def get_storage() -> Optional[ResultStorage]:
    """Get ResultStorage instance or None if unavailable."""
    if not STORAGE_AVAILABLE:
        click.secho("✗ Database storage not available", fg='red')
        return None
    
    try:
        init_database()
        return ResultStorage()
    except Exception as e:
        click.secho(f"✗ Failed to initialize database: {e}", fg='red')
        return None


@cli.group(name="res")
def result_group():
    """Result viewing and basic analysis commands.
    
    View, analyze and export experiment results.
    """
    pass


@result_group.command(name="show")
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
                'id': experiment.id,
                'name': experiment.name,
                'type': experiment.experiment_type,
                'dataset': experiment.dataset_name,
                'tags': experiment.tags,
                'created_at': experiment.created_at.isoformat() if experiment.created_at else None,
                'updated_at': experiment.updated_at.isoformat() if experiment.updated_at else None,
            }
            
            if runs:
                exp_runs = storage.get_experiment_runs(experiment.id)
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
            click.echo(f"Experiment: {experiment.name} (ID: {experiment.id})")
            click.echo("=" * 80)
            click.echo(f"Type:       {experiment.experiment_type}")
            click.echo(f"Dataset:    {experiment.dataset_name or 'N/A'}")
            click.echo(f"Tags:       {', '.join(experiment.tags) if experiment.tags else 'None'}")
            click.echo(f"Created:    {experiment.created_at.strftime('%Y-%m-%d %H:%M:%S') if experiment.created_at else 'N/A'}")
            
            if runs:
                exp_runs = storage.get_experiment_runs(experiment.id)
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
            click.echo(f"Use 'tribench res export {experiment.id}' to export results")
        
    except Exception as e:
        click.secho(f"✗ Failed to show experiment: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@result_group.command(name="list")
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


@result_group.command(name="compare")
@click.argument("experiment_ids", nargs=-1, required=True)
@click.option('--metrics', help='Metrics to compare (comma-separated).')
@click.option('--output', type=click.Path(), help='Save comparison to file.')
@verbose_option
@click.pass_context
def compare(ctx, experiment_ids, metrics, output, verbose):
    """Compare multiple experiment results.
    
    \b
    Examples:
        tribench res compare exp-001 exp-002
        tribench res compare 1 2 3
        tribench res compare 1 2 --metrics execution_time
        tribench res compare 1 2 --output comparison.json
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
                    if qe.execution_time:
                        total_execution_time += qe.execution_time
                    
                    if qe.status == 'completed':
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


@result_group.command(name="export")
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
            output = f"{experiment.name}_results.{format}"
        
        if ctx.obj.dry_run:
            click.echo(f"[DRY RUN] Would export {experiment.name} to {output}")
            return
        
        # Get all runs and query executions
        runs = storage.get_experiment_runs(experiment.id)
        
        if not runs:
            click.secho(f"✗ No runs found for experiment: {experiment.name}", fg='yellow')
            return
        
        # Collect all query executions
        all_data = []
        for run in runs:
            query_executions = storage.get_run_query_executions(run['id'])
            
            for qe in query_executions:
                row = {
                    'experiment_id': experiment.id,
                    'experiment_name': experiment.name,
                    'run_id': run['id'],
                    'run_number': run['run_number'],
                    'query_name': qe.query_name,
                    'execution_time_ms': qe.execution_time,
                    'status': qe.status,
                    'query_id': qe.query_id,
                    'input_rows': qe.input_rows,
                    'input_bytes': qe.input_bytes,
                    'cpu_time_ms': qe.cpu_time_ms,
                    'peak_memory_bytes': qe.peak_memory_bytes,
                }
                all_data.append(row)
        
        # Export based on format
        if format == 'json':
            export_data = {
                'experiment': {
                    'id': experiment.id,
                    'name': experiment.name,
                    'type': experiment.experiment_type,
                    'dataset': experiment.dataset_name,
                },
                'runs': len(runs),
                'query_executions': all_data,
            }
            
            if include_config and hasattr(experiment, 'run_metadata') and experiment.run_metadata:
                export_data['config'] = experiment.run_metadata
            
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


@result_group.command(name="analyze")
@click.argument("suite")
@click.option('--report', 
              type=click.Choice(['summary', 'detailed', 'performance', 'scalability']),
              default='summary',
              help='Type of analysis report.')
@click.option('--output', type=click.Path(), help='Save report to file.')
@click.option('--plot', is_flag=True, help='Generate plots.')
@dry_run_option
@verbose_option
@click.pass_context
def analyze(ctx, suite, report, output, plot, dry_run, verbose):
    """Analyze results from an experiment suite.
    
    \b
    Examples:
        tribench res analyze tpch-sf1
        tribench res analyze tpch-sf1 --report detailed
        tribench res analyze tpch-sf1 --report performance --plot
        tribench res analyze tpch-sf1 --output report.html
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Suite: {suite}")
        click.echo(f"Report type: {report}")
        if plot:
            click.echo("Plot generation enabled")
        if output:
            click.echo(f"Output: {output}")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would analyze suite: {suite}")
        click.echo(f"[DRY RUN] Report: {report}, Plot: {plot}")
        return
    
    # TODO: Implement result analysis
    click.secho(f"✗ Analysis for {suite} not yet implemented", fg='yellow')


@result_group.command(name="delete")
@click.argument("experiment_id")
@click.confirmation_option(prompt='Are you sure you want to delete these results?')
@verbose_option
@click.pass_context
def delete(ctx, experiment_id, verbose):
    """Delete experiment results.
    
    \b
    Examples:
        tribench res delete exp-001
        tribench res delete 1
    """
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
        
        # Delete the experiment (cascades to runs and query executions)
        with get_db_session() as session:
            session.delete(experiment)
            session.commit()
        
        click.secho(f"✓ Deleted experiment: {experiment.name} (ID: {experiment.id})", fg='green')
        
    except Exception as e:
        click.secho(f"✗ Failed to delete experiment: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@result_group.command(name="archive")
@click.option('--days', type=int, default=30, help='Archive experiments older than N days.')
@click.option('--output', type=click.Path(), help='Archive file path (default: results_archive.db).')
@click.option('--delete-archived', is_flag=True, help='Delete archived experiments from main database.')
@dry_run_option
@verbose_option
@click.pass_context
def archive(ctx, days, output, delete_archived, dry_run, verbose):
    """Archive old experiment results to reduce database size.
    
    Archives experiments older than the specified number of days to a separate
    SQLite database file. Optionally removes archived experiments from main database.
    
    \b
    Examples:
        tribench res archive --days 30
        tribench res archive --days 90 --output old_results.db
        tribench res archive --days 30 --delete-archived
        tribench res archive --dry-run
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        from datetime import timedelta
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        if ctx.obj.verbose:
            click.echo(f"Archiving experiments older than {cutoff_date.strftime('%Y-%m-%d')}")
        
        # Find experiments to archive
        with get_db_session() as session:
            from tribench.storage.models import Experiment
            
            old_experiments = (
                session.query(Experiment)
                .filter(Experiment.created_at < cutoff_date)
                .all()
            )
            
            if not old_experiments:
                click.echo("No experiments found to archive")
                return
            
            if ctx.obj.dry_run:
                click.echo(f"\n[DRY RUN] Would archive {len(old_experiments)} experiments:")
                for exp in old_experiments:
                    created = exp.created_at.strftime('%Y-%m-%d') if exp.created_at else 'N/A'
                    click.echo(f"  - {exp.name} (ID: {exp.id}, Created: {created})")
                
                if delete_archived:
                    click.echo(f"\n[DRY RUN] Would delete archived experiments from main database")
                return
            
            # Default archive file
            if not output:
                output = f"results_archive_{datetime.now().strftime('%Y%m%d')}.db"
            
            # Export experiments to archive file
            import sqlite3
            
            click.echo(f"Creating archive: {output}")
            
            # TODO: Full implementation would export to separate SQLite file
            # For now, just export as JSON
            json_output = output.replace('.db', '.json')
            
            archive_data = []
            for exp in old_experiments:
                runs = storage.get_experiment_runs(exp.id)
                
                exp_data = {
                    'id': exp.id,
                    'name': exp.name,
                    'type': exp.experiment_type,
                    'dataset': exp.dataset_name,
                    'created_at': exp.created_at.isoformat() if exp.created_at else None,
                    'runs': [],
                }
                
                for run in runs:
                    query_execs = storage.get_run_query_executions(run['id'])
                    exp_data['runs'].append({
                        'run_number': run['run_number'],
                        'status': run['status'],
                        'queries': [
                            {
                                'query_name': qe.query_name,
                                'execution_time_ms': qe.execution_time_ms,
                                'status': qe.status,
                            }
                            for qe in query_execs
                        ]
                    })
                
                archive_data.append(exp_data)
            
            # Save archive
            with open(json_output, 'w') as f:
                json.dump({'archived_experiments': archive_data}, f, indent=2)
            
            click.secho(f"✓ Archived {len(old_experiments)} experiments to {json_output}", fg='green')
            
            # Delete from main database if requested
            if delete_archived:
                for exp in old_experiments:
                    session.delete(exp)
                session.commit()
                click.secho(f"✓ Deleted {len(old_experiments)} archived experiments from database", fg='green')
        
    except Exception as e:
        click.secho(f"✗ Failed to archive results: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@result_group.command(name="monitoring")
@click.argument("run_id", type=int)
@click.option('--metric-type', help='Filter by metric type (e.g., system_resource, trino_jmx).')
@click.option('--metric-name', help='Filter by metric name (e.g., cpu_percent, memory_used).')
@click.option('--summary', is_flag=True, help='Show summary statistics instead of raw data.')
@click.option('--limit', type=int, default=100, help='Maximum number of metrics to show (default: 100).')
@click.option('--export', type=click.Path(), help='Export metrics to CSV file.')
@click.pass_context
def show_monitoring(ctx, run_id: int, metric_type: Optional[str], metric_name: Optional[str], 
                   summary: bool, limit: int, export: Optional[str]):
    """Show monitoring metrics for a specific run.
    
    Display resource monitoring data collected during an experiment run.
    Use --summary to see aggregated statistics, or view raw time-series data.
    
    Examples:
        tribench res monitoring 22 --summary
        tribench res monitoring 22 --metric-type system_resource
        tribench res monitoring 22 --metric-name cpu_percent --limit 50
        tribench res monitoring 22 --export metrics.csv
    """
    storage = get_storage()
    if not storage:
        return
    
    try:
        if summary:
            # Show summary statistics
            stats = storage.get_monitoring_metrics_summary(run_id, metric_name=metric_name)
            
            if not stats:
                click.secho(f"✗ No monitoring metrics found for run {run_id}", fg='yellow')
                return
            
            click.echo(f"\n{'Metric Name':<40} {'Count':<10} {'Min':<12} {'Max':<12} {'Mean':<12}")
            click.echo("=" * 86)
            
            for name, summary_stats in sorted(stats.items()):
                min_val = f"{summary_stats['min']:.2f}" if summary_stats['min'] is not None else "N/A"
                max_val = f"{summary_stats['max']:.2f}" if summary_stats['max'] is not None else "N/A"
                mean_val = f"{summary_stats['mean']:.2f}" if summary_stats['mean'] is not None else "N/A"
                
                click.echo(f"{name:<40} {summary_stats['count']:<10} {min_val:<12} {max_val:<12} {mean_val:<12}")
            
            click.echo()
            click.secho(f"✓ Showing summary for {len(stats)} metrics", fg='green')
        
        else:
            # Show raw metrics
            metrics = storage.get_monitoring_metrics(
                run_id=run_id,
                metric_type=metric_type,
                metric_name=metric_name,
                limit=limit
            )
            
            if not metrics:
                click.secho(f"✗ No monitoring metrics found for run {run_id}", fg='yellow')
                return
            
            if export:
                # Export to CSV
                import csv
                with open(export, 'w', newline='') as f:
                    if metrics:
                        fieldnames = list(metrics[0].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(metrics)
                click.secho(f"✓ Exported {len(metrics)} metrics to {export}", fg='green')
            else:
                # Display in terminal
                click.echo(f"\n{'Timestamp':<22} {'Type':<18} {'Name':<30} {'Value':<12} {'Unit':<10}")
                click.echo("=" * 92)
                
                for m in metrics:
                    timestamp = m['timestamp'][:19]  # Trim to seconds
                    value = f"{m['value']:.2f}" if m['value'] is not None else m['value_text'] or "N/A"
                    unit = m['unit'] or ""
                    
                    click.echo(f"{timestamp:<22} {m['metric_type']:<18} {m['metric_name']:<30} {value:<12} {unit:<10}")
                
                click.echo()
                click.secho(f"✓ Showing {len(metrics)} metrics" + (f" (limit: {limit})" if len(metrics) == limit else ""), fg='green')
    
    except Exception as e:
        click.secho(f"✗ Failed to retrieve monitoring metrics: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@result_group.command(name="reset-db")
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt.')
@click.pass_context
def reset_database(ctx, confirm):
    """Reset the database by deleting all experiments and data.
    
    This command will delete ALL experiments, runs, query executions, 
    and monitoring metrics from the database. This action cannot be undone.
    
    Use with caution!
    
    Examples:
        tribench res reset-db
        tribench res reset-db --confirm
    """
    storage = get_storage()
    if not storage:
        return
    
    try:
        from tribench.storage.connection import get_db_session
        from tribench.storage.models import (
            Experiment, 
            ExperimentRun, 
            QueryExecution, 
            SystemMetric,
            MonitoringMetric
        )
        
        # Get count of experiments before deletion
        with get_db_session() as session:
            exp_count = session.query(Experiment).count()
            run_count = session.query(ExperimentRun).count()
            query_count = session.query(QueryExecution).count()
            metric_count = session.query(MonitoringMetric).count()
        
        if exp_count == 0:
            click.secho("✓ Database is already empty", fg='green')
            return
        
        # Show what will be deleted
        click.echo("\n" + "=" * 80)
        click.secho("⚠️  WARNING: Database Reset", fg='yellow', bold=True)
        click.echo("=" * 80)
        click.echo(f"This will permanently delete:")
        click.echo(f"  • {exp_count} experiments")
        click.echo(f"  • {run_count} experiment runs")
        click.echo(f"  • {query_count} query executions")
        click.echo(f"  • {metric_count} monitoring metrics")
        click.echo("=" * 80)
        
        if not confirm:
            click.echo()
            confirm_input = click.prompt(
                "Type 'DELETE' to confirm (or anything else to cancel)",
                type=str,
                default="cancel"
            )
            
            if confirm_input != "DELETE":
                click.secho("✓ Database reset cancelled", fg='green')
                return
        
        # Perform deletion
        click.echo()
        click.echo("Resetting database...")
        
        with get_db_session() as session:
            # Delete all data (cascade will handle related records)
            deleted_count = session.query(Experiment).delete()
            session.commit()
            
            click.secho(f"✓ Deleted {deleted_count} experiments and all associated data", fg='green')
            click.echo()
            click.echo("Database has been reset successfully")
        
    except Exception as e:
        click.secho(f"✗ Failed to reset database: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
