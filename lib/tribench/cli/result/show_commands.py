"""
Result display commands.

Commands for showing and listing experiment results.
"""

import click
import json
import statistics
from pathlib import Path
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


@click.command(name="suite-summary")
@click.argument("suite_id")
@click.option('--format',
              type=click.Choice(['table', 'json']),
              default='table',
              help='Output format.')
@click.option('--warmup/--no-warmup',
              default=False,
              help='Include warmup runs in aggregation (default: measured runs only).')
@verbose_option
@click.pass_context
def suite_summary(ctx, suite_id, format, warmup, verbose):
    """Show aggregated results summary for all experiments in a suite.

    SUITE_ID can be a suite name (resolved from the active bundle's
    experiments/suites/ directory), a bare filename, or a full path.

    \b
    Examples:
        tribench res suite-summary gke-suite
        tribench res suite-summary gke-suite.yaml
        tribench res suite-summary experiments/suites/gke-suite.yaml
        tribench res suite-summary gke-suite --format json
        tribench res suite-summary gke-suite --warmup
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose

    # Resolve suite path using the same logic as `tribench suite run`:
    # 1. As-is (absolute or relative from cwd)
    # 2. With .yaml appended
    # 3. Inside bundle_root/experiments/suites/
    # 4. Inside bundle_root/experiments/suites/ with .yaml appended
    bundle_root = getattr(ctx.obj, 'bundle_root', None)

    def _candidates(sid):
        p = Path(sid)
        yield p
        if p.suffix != '.yaml':
            yield p.with_suffix('.yaml')
        if bundle_root:
            base = Path(bundle_root) / 'experiments' / 'suites'
            yield base / p
            if p.suffix != '.yaml':
                yield base / p.with_suffix('.yaml')

    suite_path = None
    for candidate in _candidates(suite_id):
        if candidate.exists():
            suite_path = candidate
            break

    if suite_path is None:
        click.secho(f"✗ Suite not found: {suite_id}", fg='red')
        if bundle_root:
            click.secho(
                f"  Looked in: . and {Path(bundle_root) / 'experiments' / 'suites'}", fg='red'
            )
        return

    # Load suite definition
    try:
        from tribench.core.experiment_suite import ExperimentSuite
        suite = ExperimentSuite.from_yaml(str(suite_path))
    except Exception as e:
        click.secho(f"✗ Failed to load suite '{suite_id}': {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        return

    storage = get_storage()
    if not storage:
        return

    # ------------------------------------------------------------------ #
    # Collect per-experiment statistics                                    #
    # ------------------------------------------------------------------ #
    experiment_stats = []

    for exp_config in suite.experiments:
        exp_name = exp_config.name
        experiment = storage.get_experiment_by_name(exp_name)

        if not experiment:
            experiment_stats.append({
                'name': exp_name,
                'status': 'NOT_FOUND',
                'total_runs': 0,
                'total_queries': 0,
                'succeeded': 0,
                'failed': 0,
                'mean_exec_ms': None,
                'median_exec_ms': None,
                'p95_exec_ms': None,
                'min_exec_ms': None,
                'max_exec_ms': None,
                'total_cpu_s': 0.0,
                'total_data_gb': 0.0,
            })
            continue

        runs = storage.get_experiment_runs(experiment['id'])

        # Keep only measured runs unless --warmup flag is set
        if not warmup:
            measured = [r for r in runs if r.get('run_type') != 'warmup']
            if not measured:
                measured = runs  # fallback: no run_type metadata stored
        else:
            measured = runs

        all_exec_ms = []
        total_queries = 0
        total_succeeded = 0
        total_failed = 0
        total_cpu_ms = 0.0
        total_input_bytes = 0

        for run in measured:
            query_execs = storage.get_run_query_executions(run['id'])
            for qe in query_execs:
                total_queries += 1
                if qe.get('status') == 'success':
                    total_succeeded += 1
                    if qe.get('execution_time') is not None:
                        all_exec_ms.append(qe['execution_time'] * 1000.0)
                else:
                    total_failed += 1
                total_cpu_ms += qe.get('cpu_time_ms') or 0.0
                total_input_bytes += qe.get('input_bytes') or 0

        if all_exec_ms:
            sorted_ms = sorted(all_exec_ms)
            n = len(sorted_ms)
            mean_ms = sum(sorted_ms) / n
            median_ms = statistics.median(sorted_ms)
            p95_ms = sorted_ms[min(int(n * 0.95), n - 1)]
            min_ms = sorted_ms[0]
            max_ms = sorted_ms[-1]
        else:
            mean_ms = median_ms = p95_ms = min_ms = max_ms = None

        experiment_stats.append({
            'name': exp_name,
            'exp_id': experiment['id'],
            'status': 'OK',
            'total_runs': len(measured),
            'total_queries': total_queries,
            'succeeded': total_succeeded,
            'failed': total_failed,
            'mean_exec_ms': mean_ms,
            'median_exec_ms': median_ms,
            'p95_exec_ms': p95_ms,
            'min_exec_ms': min_ms,
            'max_exec_ms': max_ms,
            'total_cpu_s': total_cpu_ms / 1000.0,
            'total_data_gb': total_input_bytes / (1024 ** 3),
        })

    # ------------------------------------------------------------------ #
    # Output                                                               #
    # ------------------------------------------------------------------ #
    if format == 'json':
        output = {
            'suite': suite.name,
            'suite_id': suite_id,
            'suite_path': str(suite_path),
            'description': getattr(suite, 'description', None),
            'include_warmup': warmup,
            'experiments': experiment_stats,
        }
        click.echo(json.dumps(output, indent=2, default=str))
        return

    # Table output
    W = 138
    click.echo("\n" + "=" * W)
    click.echo(f"Suite Summary: {suite.name}")
    if getattr(suite, 'description', None):
        click.echo(f"Description:   {suite.description}")
    click.echo(f"Suite Path:    {suite_path}")
    click.echo(f"Experiments:   {len(suite.experiments)}"
               + ("  (warmup runs included)" if warmup else "  (measured runs only)"))
    click.echo("=" * W)

    hdr = (f"\n{'Experiment':<34} {'Runs':<6} {'Queries':<10} {'Succ%':<8}"
           f" {'Mean(ms)':<12} {'Median(ms)':<12} {'P95(ms)':<11}"
           f" {'Min(ms)':<10} {'Max(ms)':<10} {'CPU(s)':<10} {'Data(GB)':<9}")
    click.echo(hdr)
    click.echo("-" * W)

    def _fmt(val, decimals=1):
        return f"{val:.{decimals}f}" if val is not None else "N/A"

    ok_stats = []
    for s in experiment_stats:
        if s['status'] == 'NOT_FOUND':
            click.secho(
                f"  {s['name'][:32]:<34} {'—':<6} {'—':<10} {'—':<8}"
                f" {'—':<12} {'—':<12} {'—':<11} {'—':<10} {'—':<10} {'—':<10} {'—':<9}"
                f"  ← not in DB",
                fg='yellow',
            )
            continue

        ok_stats.append(s)
        succ_pct = (f"{100.0 * s['succeeded'] / s['total_queries']:.1f}%"
                    if s['total_queries'] > 0 else "N/A")

        click.echo(
            f"  {s['name'][:32]:<34} {s['total_runs']:<6} {s['total_queries']:<10} {succ_pct:<8}"
            f" {_fmt(s['mean_exec_ms']):<12} {_fmt(s['median_exec_ms']):<12}"
            f" {_fmt(s['p95_exec_ms']):<11} {_fmt(s['min_exec_ms']):<10}"
            f" {_fmt(s['max_exec_ms']):<10} {_fmt(s['total_cpu_s']):<10}"
            f" {_fmt(s['total_data_gb'], 3):<9}"
        )

    click.echo("-" * W)

    # Totals row
    if ok_stats:
        tot_runs = sum(s['total_runs'] for s in ok_stats)
        tot_q = sum(s['total_queries'] for s in ok_stats)
        tot_succ = sum(s['succeeded'] for s in ok_stats)
        tot_fail = sum(s['failed'] for s in ok_stats)
        means = [s['mean_exec_ms'] for s in ok_stats if s['mean_exec_ms'] is not None]
        overall_mean = sum(means) / len(means) if means else None
        overall_cpu = sum(s['total_cpu_s'] for s in ok_stats)
        overall_gb = sum(s['total_data_gb'] for s in ok_stats)
        overall_pct = (f"{100.0 * tot_succ / tot_q:.1f}%" if tot_q > 0 else "N/A")

        click.echo(
            f"  {'TOTAL':<34} {tot_runs:<6} {tot_q:<10} {overall_pct:<8}"
            f" {_fmt(overall_mean):<12} {'—':<12} {'—':<11} {'—':<10} {'—':<10}"
            f" {_fmt(overall_cpu):<10} {_fmt(overall_gb, 3):<9}"
        )

    click.echo("=" * W)

    not_found = [s['name'] for s in experiment_stats if s['status'] == 'NOT_FOUND']
    if ok_stats:
        click.echo(
            f"\nTotal failed queries: {sum(s['failed'] for s in ok_stats)}"
        )
    if not_found:
        click.secho(
            f"Experiments not yet in DB: {', '.join(not_found)}", fg='yellow'
        )
    click.echo("Use --format json for full data export")
