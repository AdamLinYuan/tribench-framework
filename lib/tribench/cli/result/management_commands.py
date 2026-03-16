"""
Result management commands.

Commands for deleting, archiving, and managing experiment data.
"""

import click
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from tribench.cli.base import dry_run_option, verbose_option
from .utils import get_storage

try:
    from tribench.storage.connection import get_db_session
    from tribench.storage.models import (
        Experiment,
        ExperimentRun,
        QueryExecution,
        SystemMetric,
        MonitoringMetric
    )
except ImportError:
    pass


@click.command(name="delete")
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
        from tribench.storage.models import Experiment
        with get_db_session() as session:
            orm_exp = session.query(Experiment).filter(Experiment.id == experiment['id']).first()
            if orm_exp is None:
                click.secho(f"✗ Experiment not found in database: {experiment_id}", fg='red')
                return
            session.delete(orm_exp)
            session.commit()
        
        click.secho(f"✓ Deleted experiment: {experiment['name']} (ID: {experiment['id']})", fg='green')
        
    except Exception as e:
        click.secho(f"✗ Failed to delete experiment: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@click.command(name="archive")
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


@click.command(name="monitoring")
@click.argument("experiment_id", type=int)
@click.option('--run', 'run_number', type=int, help='Specific run number to show metrics for. If not specified, shows aggregate across all runs.')
@click.option('--metric-type', help='Filter by metric type (e.g., system_resource, trino_jmx).')
@click.option('--metric-name', help='Filter by metric name (e.g., cpu_percent, memory_used).')
@click.option('--summary', is_flag=True, help='Show summary statistics instead of raw data.')
@click.option('--limit', type=int, default=100, help='Maximum number of metrics to show (default: 100).')
@click.option('--export', type=click.Path(), help='Export metrics to CSV file.')
@click.pass_context
def show_monitoring(ctx, experiment_id: int, run_number: Optional[int], metric_type: Optional[str], 
                   metric_name: Optional[str], summary: bool, limit: int, export: Optional[str]):
    """Show monitoring metrics for an experiment.
    
    Display resource monitoring data collected during an experiment.
    By default shows aggregated metrics across all runs. Use --run to specify a single run.
    Use --summary to see aggregated statistics, or view raw time-series data.
    
    Examples:
        tribench res monitoring 13 --summary  (aggregate across all runs)
        tribench res monitoring 13 --run 5 --summary  (specific run only)
        tribench res monitoring 13 --metric-type system_resource
        tribench res monitoring 13 --run 3 --metric-name cpu_percent --limit 50
        tribench res monitoring 13 --export metrics.csv
    """
    storage = get_storage()
    if not storage:
        return
    
    try:
        # Get experiment information
        experiment_info = storage.get_experiment_by_id(experiment_id)
        if not experiment_info:
            click.secho(f"✗ Experiment {experiment_id} not found", fg='red')
            return
        
        # Get all runs for the experiment
        exp_runs = storage.get_experiment_runs(experiment_id)
        if not exp_runs:
            click.secho(f"✗ No runs found for experiment {experiment_id}", fg='yellow')
            return
        
        if run_number is not None:
            # Show metrics for specific run
            run_info = next((r for r in exp_runs if r['run_number'] == run_number), None)
            if not run_info:
                click.secho(f"✗ Run {run_number} not found for experiment {experiment_id}", fg='red')
                return
            run_ids = [run_info['id']]
            display_run_info = f"Run: {run_info['run_number']} (Run ID: {run_info['id']})"
        else:
            # Aggregate metrics across all runs
            run_ids = [r['id'] for r in exp_runs]
            display_run_info = f"Aggregated across {len(run_ids)} runs"
        
        if summary:
            # Collect and aggregate statistics from all specified runs
            all_stats = {}
            
            for run_id in run_ids:
                stats = storage.get_monitoring_metrics_summary(run_id, metric_name=metric_name)
                if stats:
                    for metric_name_key, metric_stats in stats.items():
                        if metric_name_key not in all_stats:
                            all_stats[metric_name_key] = {
                                'counts': [],
                                'mins': [],
                                'maxs': [],
                                'means': []
                            }
                        all_stats[metric_name_key]['counts'].append(metric_stats['count'])
                        all_stats[metric_name_key]['mins'].append(metric_stats['min'])
                        all_stats[metric_name_key]['maxs'].append(metric_stats['max'])
                        all_stats[metric_name_key]['means'].append(metric_stats['mean'])
            
            if not all_stats:
                click.secho(f"✗ No monitoring metrics found", fg='yellow')
                return
            
            # Calculate aggregated statistics
            aggregated_stats = {}
            for metric_name_key, values in all_stats.items():
                aggregated_stats[metric_name_key] = {
                    'count': sum(values['counts']),
                    'min': min(values['mins']) if values['mins'] else None,
                    'max': max(values['maxs']) if values['maxs'] else None,
                    'mean': sum(values['means']) / len(values['means']) if values['means'] else None
                }
            
            # Display experiment and run information
            click.echo("\n" + "=" * 86)
            click.echo(f"Experiment ID: {experiment_id}")
            click.echo(f"Experiment Name: {experiment_info.get('name', 'N/A')}")
            click.echo(f"{display_run_info}")
            click.echo("=" * 86)
            
            click.echo(f"\n{'Metric Name':<40} {'Count':<10} {'Min':<12} {'Max':<12} {'Mean':<12}")
            click.echo("=" * 86)
            
            for name, summary_stats in sorted(aggregated_stats.items()):
                min_val = f"{summary_stats['min']:.2f}" if summary_stats['min'] is not None else "N/A"
                max_val = f"{summary_stats['max']:.2f}" if summary_stats['max'] is not None else "N/A"
                mean_val = f"{summary_stats['mean']:.2f}" if summary_stats['mean'] is not None else "N/A"
                
                click.echo(f"{name:<40} {summary_stats['count']:<10} {min_val:<12} {max_val:<12} {mean_val:<12}")
            
            click.echo()
            click.secho(f"✓ Showing summary for {len(aggregated_stats)} metrics", fg='green')
        
        else:
            # Show raw metrics - need to handle multiple runs
            if len(run_ids) > 1:
                click.secho("⚠ Raw metrics view requires a specific run. Use --run <number> or add --summary for aggregated view.", fg='yellow')
                return
            
            run_id = run_ids[0]
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


@click.command(name="reset-db")
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
