"""
Result display commands.

Commands for showing and listing experiment results.
"""

import click
import json
from tribench.cli.base import verbose_option
from .utils import get_storage


@click.command(name="queries")
@click.argument("run_id", type=int)
@click.option('--format', 
              type=click.Choice(['table', 'json']),
              default='table',
              help='Output format.')
@click.option('--query', help='Filter by specific query name.')
@click.option('--show-hash', is_flag=True, help='Show query plan hash.')
@click.option('--summary', is_flag=True, help='Show summary statistics instead of individual queries.')
@verbose_option
@click.pass_context
def show_queries(ctx, run_id, format, query, show_hash, summary, verbose):
    """Show detailed query execution metrics for a run.
    
    Displays advanced metrics including planning/analysis time, splits, 
    tasks, spilled bytes, and query plan hash.
    
    \\b
    Examples:
        tribench res queries 1
        tribench res queries 1 --query q01
        tribench res queries 1 --format json
        tribench res queries 1 --show-hash
        tribench res queries 1 --summary
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        # Get run info
        from tribench.storage.connection import get_db_session
        from tribench.storage.models import ExperimentRun
        
        with get_db_session() as session:
            run = session.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()
            if not run:
                click.secho(f"✗ Run {run_id} not found", fg='red')
                return
            
            experiment_id = run.experiment_id
        
        experiment = storage.get_experiment_by_id(experiment_id)
        
        # Get query executions
        query_executions = storage.get_run_query_executions(run_id)
        
        if not query_executions:
            click.secho(f"✗ No query executions found for run {run_id}", fg='yellow')
            return
        
        # Filter by query name if specified
        if query:
            query_executions = [qe for qe in query_executions if qe['query_name'] == query]
            if not query_executions:
                click.secho(f"✗ No executions found for query {query}", fg='red')
                return
        
        # Calculate summary statistics if requested
        if summary:
            total_queries = len(query_executions)
            total_exec_time = sum(qe.get('execution_time', 0) or 0 for qe in query_executions)
            total_cpu_time = sum(qe.get('cpu_time_ms', 0) or 0 for qe in query_executions)
            total_input_rows = sum(qe.get('input_rows', 0) or 0 for qe in query_executions)
            total_input_bytes = sum(qe.get('input_bytes', 0) or 0 for qe in query_executions)
            total_peak_memory = sum(qe.get('peak_memory_bytes', 0) or 0 for qe in query_executions)
            total_spilled = sum(qe.get('spilled_bytes', 0) or 0 for qe in query_executions)
            total_splits = sum(qe.get('total_splits', 0) or 0 for qe in query_executions)
            completed_splits = sum(qe.get('completed_splits', 0) or 0 for qe in query_executions)
            total_tasks = sum(qe.get('total_tasks', 0) or 0 for qe in query_executions)
            
            avg_exec_time = total_exec_time / total_queries if total_queries > 0 else 0
            avg_cpu_time = total_cpu_time / total_queries if total_queries > 0 else 0
            
            if format == 'json':
                summary_data = {
                    'run_id': run_id,
                    'experiment_name': experiment['name'],
                    'total_queries': total_queries,
                    'total_execution_time_ms': total_exec_time * 1000,
                    'avg_execution_time_ms': avg_exec_time * 1000,
                    'total_cpu_time_ms': total_cpu_time,
                    'avg_cpu_time_ms': avg_cpu_time,
                    'total_input_rows': total_input_rows,
                    'total_input_bytes': total_input_bytes,
                    'total_peak_memory_bytes': total_peak_memory,
                    'total_spilled_bytes': total_spilled,
                    'total_splits': total_splits,
                    'completed_splits': completed_splits,
                    'total_tasks': total_tasks,
                }
                click.echo(json.dumps(summary_data, indent=2))
            else:
                click.echo("\n" + "=" * 80)
                click.echo(f"Query Execution Summary - Run {run_id} ({experiment['name']})") 
                click.echo("=" * 80)
                click.echo(f"\nTotal Queries:           {total_queries}")
                click.echo(f"\nExecution Metrics:")
                click.echo(f"  Total Execution Time:  {total_exec_time * 1000:.2f}ms")
                click.echo(f"  Avg Execution Time:    {avg_exec_time * 1000:.2f}ms")
                click.echo(f"  Total CPU Time:        {total_cpu_time:.0f}ms")
                click.echo(f"  Avg CPU Time:          {avg_cpu_time:.0f}ms")
                click.echo(f"\nData Processing:")
                click.echo(f"  Total Input Rows:      {total_input_rows:,}")
                click.echo(f"  Total Input Bytes:     {total_input_bytes / 1024 / 1024:.2f}MB")
                click.echo(f"  Total Peak Memory:     {total_peak_memory / 1024 / 1024:.2f}MB")
                click.echo(f"\nAdvanced Metrics:")
                click.echo(f"  Total Splits:          {total_splits:,}")
                click.echo(f"  Completed Splits:      {completed_splits:,}")
                click.echo(f"  Total Tasks:           {total_tasks:,}")
                click.echo(f"  Total Spilled Bytes:   {total_spilled:,}B")
                click.echo("=" * 80)
            return
        
        if format == 'json':
            # JSON output with all metrics
            output_data = {
                'run_id': run_id,
                'experiment_name': experiment['name'],
                'query_executions': []
            }
            
            for qe in query_executions:
                query_data = {
                    'query_name': qe['query_name'],
                    'query_id': qe['query_id'],
                    'status': qe['status'],
                    'execution_time_ms': qe['execution_time'] * 1000 if qe.get('execution_time') else None,
                    'cpu_time_ms': qe.get('cpu_time_ms'),
                    'planning_time_ms': qe.get('planning_time_ms'),
                    'analysis_time_ms': qe.get('analysis_time_ms'),
                    'input_rows': qe.get('input_rows'),
                    'input_bytes': qe.get('input_bytes'),
                    'peak_memory_bytes': qe.get('peak_memory_bytes'),
                    'spilled_bytes': qe.get('spilled_bytes'),
                    'total_splits': qe.get('total_splits'),
                    'completed_splits': qe.get('completed_splits'),
                    'total_tasks': qe.get('total_tasks'),
                    'query_plan_hash': qe.get('query_plan_hash'),
                }
                output_data['query_executions'].append(query_data)
            
            click.echo(json.dumps(output_data, indent=2))
        
        else:
            # Table output
            click.echo("\n" + "=" * 140)
            click.echo(f"Query Execution Metrics - Run {run_id} ({experiment['name']})")
            click.echo("=" * 140)
            
            # Basic metrics table
            click.echo("\nExecution Overview:")
            click.echo("-" * 140)
            click.echo(f"{'Query':<10} {'Status':<10} {'Exec Time':<12} {'CPU Time':<12} {'Input Rows':<14} {'Input Bytes':<14} {'Peak Memory':<14}")
            click.echo("-" * 140)
            
            for qe in query_executions:
                exec_time = f"{qe['execution_time']*1000:.2f}ms" if qe.get('execution_time') else "N/A"
                cpu_time = f"{qe.get('cpu_time_ms') or 0:.0f}ms"
                input_rows = f"{qe.get('input_rows') or 0:,}"
                input_bytes = f"{(qe.get('input_bytes') or 0) / 1024 / 1024:.2f}MB"
                peak_mem = f"{(qe.get('peak_memory_bytes') or 0) / 1024 / 1024:.2f}MB"
                
                click.echo(
                    f"{qe['query_name']:<10} {qe['status']:<10} {exec_time:<12} {cpu_time:<12} "
                    f"{input_rows:<14} {input_bytes:<14} {peak_mem:<14}"
                )
            
            # Advanced metrics table
            click.echo("\n" + "-" * 140)
            click.echo("Advanced Metrics:")
            click.echo("-" * 140)
            header = f"{'Query':<10} {'Plan Time':<12} {'Analyze Time':<15} {'Splits (C/T)':<16} {'Tasks':<10} {'Spilled Bytes':<15}"
            if show_hash:
                header += f" {'Plan Hash':<20}"
            click.echo(header)
            click.echo("-" * 140)
            
            for qe in query_executions:
                plan_time = f"{qe.get('planning_time_ms') or 0:.2f}ms" if qe.get('planning_time_ms') else "N/A"
                analyze_time = f"{qe.get('analysis_time_ms') or 0:.2f}ms" if qe.get('analysis_time_ms') else "N/A"
                splits = f"{qe.get('completed_splits') or 0}/{qe.get('total_splits') or 0}"
                tasks = str(qe.get('total_tasks') or 0)
                spilled = f"{(qe.get('spilled_bytes') or 0):,}B"
                
                line = f"{qe['query_name']:<10} {plan_time:<12} {analyze_time:<15} {splits:<16} {tasks:<10} {spilled:<15}"
                if show_hash:
                    plan_hash = qe.get('query_plan_hash') or 'N/A'
                    line += f" {plan_hash[:20]:<20}"
                click.echo(line)
            
            click.echo("=" * 140)
            click.echo(f"\nTotal queries: {len(query_executions)}")
            if not show_hash:
                click.echo("Use --show-hash to display query plan hashes")
            click.echo(f"Use --format json for complete data export")
        
    except Exception as e:
        click.secho(f"✗ Failed to show queries: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@click.command(name="show")
@click.argument("experiment_id")
@click.option('--format', 
              type=click.Choice(['table', 'json', 'yaml']),
              default='table',
              help='Output format.')
@click.option('--metrics', help='Comma-separated list of metrics to show.')
@click.option('--runs', is_flag=True, help='Show all runs for this experiment.')
@click.option('--queries', is_flag=True, help='Show query execution details with advanced metrics.')
@verbose_option
@click.pass_context
def show(ctx, experiment_id, format, metrics, runs, queries, verbose):
    """Show experiment results.
    
    \b
    Examples:
        tribench res show exp-001
        tribench res show 1 --format json
        tribench res show 1 --runs
        tribench res show 1 --queries
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
                click.echo(f"{'Run ID':<8} {'Run':<6} {'Status':<12} {'Duration(s)':<15} {'Queries':<10} {'Success':<10} {'Failed':<10} {'Monitoring':<12}")
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
                        f"{r['id']:<8} {r['run_number']:<6} {r['status']:<12} {duration:<15} "
                        f"{r.get('queries_total') or 0:<10} {r.get('queries_succeeded') or 0:<10} "
                        f"{r.get('queries_failed') or 0:<10} {monitoring_info:<12}"
                    )
                click.echo("-" * 100)
            
            # Show query execution details if requested
            if queries:
                exp_runs = storage.get_experiment_runs(experiment['id'])
                click.echo("\n" + "=" * 140)
                click.echo("Query Execution Details (Advanced Metrics)")
                click.echo("=" * 140)
                
                for r in exp_runs:
                    query_execs = storage.get_run_query_executions(r['id'])
                    if query_execs:
                        click.echo(f"\nRun {r['run_number']}:")
                        click.echo("-" * 140)
                        click.echo(f"{'Query':<10} {'Status':<10} {'Exec(ms)':<12} {'CPU(ms)':<10} {'Plan(ms)':<10} {'Analyze(ms)':<12} {'Splits':<12} {'Tasks':<8} {'Spilled':<12}")
                        click.echo("-" * 140)
                        
                        for qe in query_execs:
                            exec_time = f"{qe['execution_time']*1000:.1f}" if qe.get('execution_time') else "N/A"
                            cpu_time = f"{qe.get('cpu_time_ms') or 0:.0f}"
                            plan_time = f"{qe.get('planning_time_ms') or 0:.1f}" if qe.get('planning_time_ms') else "N/A"
                            analyze_time = f"{qe.get('analysis_time_ms') or 0:.1f}" if qe.get('analysis_time_ms') else "N/A"
                            splits = f"{qe.get('completed_splits') or 0}/{qe.get('total_splits') or 0}"
                            tasks = f"{qe.get('total_tasks') or 0}"
                            spilled = f"{qe.get('spilled_bytes') or 0}"
                            
                            click.echo(
                                f"{qe['query_name']:<10} {qe['status']:<10} {exec_time:<12} {cpu_time:<10} "
                                f"{plan_time:<10} {analyze_time:<12} {splits:<12} {tasks:<8} {spilled:<12}"
                            )
                        click.echo("-" * 140)
            
            click.echo("=" * 80)
            click.echo(f"\nUse '--runs' to see all runs")
            click.echo(f"Use '--queries' to see query execution details with advanced metrics")
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
