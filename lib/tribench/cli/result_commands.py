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

# Import analysis modules
try:
    from tribench.analysis import (
        StatisticalAnalyzer,
        PerformanceAnalyzer,
        ComparisonAnalyzer,
        ScalabilityAnalyzer,
        RegressionDetector,
    )
    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False


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


@result_group.group(name="analyze")
@click.pass_context
def analyze_group(ctx):
    """Analyze experiment results.
    
    \b
    Examples:
        tribench res analyze statistics <experiment_id>
        tribench res analyze performance <experiment_id>
        tribench res analyze compare <baseline_id> <current_id>
        tribench res analyze scalability <baseline_id> <scaled_id>
        tribench res analyze regression <baseline_id> <current_id>
    """
    pass


@analyze_group.command(name="statistics")
@click.argument("experiment_id", type=int)
@click.option('--query', help='Analyze specific query only.')
@click.option('--format', 'output_format', 
              type=click.Choice(['text', 'json', 'csv']),
              default='text',
              help='Output format.')
@click.option('--output', type=click.Path(), help='Save report to file.')
@verbose_option
@click.pass_context
def analyze_statistics(ctx, experiment_id, query, output_format, output, verbose):
    """Analyze query execution statistics.
    
    Computes descriptive statistics (mean, median, stddev, percentiles)
    and detects outliers for query execution times.
    
    \b
    Examples:
        tribench res analyze statistics 1
        tribench res analyze statistics 1 --query "Q1"
        tribench res analyze statistics 1 --format json --output stats.json
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if not STORAGE_AVAILABLE or not ANALYSIS_AVAILABLE:
        click.secho("✗ Analysis requires storage and analysis modules", fg='red')
        return
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        # Get experiment
        experiment = storage.get_experiment_by_id(experiment_id)
        if not experiment:
            click.secho(f"✗ Experiment {experiment_id} not found", fg='red')
            return
        
        # Get runs
        runs = storage.get_experiment_runs(experiment_id)
        if not runs:
            click.secho(f"✗ No runs found for experiment {experiment_id}", fg='red')
            return
        
        # Collect query executions
        all_executions = []
        for run in runs:
            executions = storage.get_run_query_executions(run['id'])
            all_executions.extend([{
                'run_id': run['id'],
                'query_name': e['query_name'],
                'execution_time': e['execution_time'],
                'rows_processed': e['input_rows'],
                'bytes_processed': e['input_bytes'],
            } for e in executions])
        
        if not all_executions:
            click.secho(f"✗ No query executions found", fg='red')
            return
        
        # Filter by query if specified
        if query:
            all_executions = [e for e in all_executions if e['query_name'] == query]
            if not all_executions:
                click.secho(f"✗ No executions found for query {query}", fg='red')
                return
        
        # Analyze statistics
        analyzer = StatisticalAnalyzer()
        
        # Group by query name
        query_groups = {}
        for execution in all_executions:
            qname = execution['query_name']
            if qname not in query_groups:
                query_groups[qname] = []
            query_groups[qname].append(execution['execution_time'])
        
        # Calculate statistics for each query
        results = {}
        for qname, times in query_groups.items():
            stats = analyzer.calculate_statistics(times)
            outliers = analyzer.detect_outliers(times, method='iqr')
            ci = analyzer.calculate_confidence_interval(times, confidence=0.95)
            
            results[qname] = {
                'statistics': stats,
                'outliers': outliers,
                'confidence_interval': ci,
                'sample_size': len(times)
            }
        
        # Output results
        if output_format == 'json':
            output_data = {
                'experiment_id': experiment_id,
                'experiment_name': experiment['name'],
                'query_filter': query,
                'total_runs': len(runs),
                'results': results
            }
            json_str = json.dumps(output_data, indent=2)
            
            if output:
                Path(output).write_text(json_str)
                click.secho(f"✓ Statistics saved to {output}", fg='green')
            else:
                click.echo(json_str)
        
        elif output_format == 'csv':
            import csv
            from io import StringIO
            
            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(['query', 'metric', 'value'])
            
            for qname, data in results.items():
                stats = data['statistics']
                for metric, value in stats.items():
                    writer.writerow([qname, metric, value])
            
            csv_str = csv_buffer.getvalue()
            
            if output:
                Path(output).write_text(csv_str)
                click.secho(f"✓ Statistics saved to {output}", fg='green')
            else:
                click.echo(csv_str)
        
        else:  # text format
            lines = []
            lines.append(f"\n📊 Statistical Analysis for Experiment {experiment_id}: {experiment['name']}")
            lines.append(f"Total Runs: {len(runs)}")
            if query:
                lines.append(f"Query Filter: {query}")
            lines.append("")
            
            for qname in sorted(results.keys()):
                data = results[qname]
                stats = data['statistics']
                outliers = data['outliers']
                ci = data['confidence_interval']
                
                lines.append(f"Query: {qname}")
                lines.append(f"  Sample Size: {data['sample_size']}")
                lines.append(f"  Mean:        {stats['mean']:.3f}s")
                lines.append(f"  Median:      {stats['median']:.3f}s")
                lines.append(f"  Std Dev:     {stats['stdev']:.3f}s")
                lines.append(f"  Min:         {stats['min']:.3f}s")
                lines.append(f"  Max:         {stats['max']:.3f}s")
                lines.append(f"  P50:         {stats['p50']:.3f}s")
                lines.append(f"  P95:         {stats['p95']:.3f}s")
                lines.append(f"  P99:         {stats['p99']:.3f}s")
                lines.append(f"  95% CI:      [{ci['lower_bound']:.3f}s, {ci['upper_bound']:.3f}s]")
                lines.append(f"  Outliers:    {len(outliers['outliers'])} detected")
                if outliers['outliers']:
                    lines.append(f"    Values: {', '.join(f'{v:.3f}' for v in outliers['outliers'][:5])}")
                lines.append("")
            
            text_output = '\n'.join(lines)
            
            if output:
                Path(output).write_text(text_output)
                click.secho(f"✓ Statistics saved to {output}", fg='green')
            else:
                click.echo(text_output)
    
    except Exception as e:
        click.secho(f"✗ Analysis failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@analyze_group.command(name="performance")
@click.argument("experiment_id", type=int)
@click.option('--query', help='Analyze specific query only.')
@click.option('--breakdown', is_flag=True, help='Show per-query breakdown.')
@click.option('--format', 'output_format', 
              type=click.Choice(['text', 'json']),
              default='text',
              help='Output format.')
@click.option('--output', type=click.Path(), help='Save report to file.')
@verbose_option
@click.pass_context
def analyze_performance(ctx, experiment_id, query, breakdown, output_format, output, verbose):
    """Analyze experiment performance metrics.
    
    Analyzes execution time, throughput (QPS), and resource efficiency
    for queries in an experiment.
    
    \b
    Examples:
        tribench res analyze performance 1
        tribench res analyze performance 1 --query "Q1"
        tribench res analyze performance 1 --breakdown --format json
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if not STORAGE_AVAILABLE or not ANALYSIS_AVAILABLE:
        click.secho("✗ Analysis requires storage and analysis modules", fg='red')
        return
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        analyzer = PerformanceAnalyzer(storage=storage)
        
        if query:
            # Analyze specific query
            result = analyzer.analyze_query_performance(experiment_id, query)
            
            if output_format == 'json':
                json_str = json.dumps(result, indent=2)
                if output:
                    Path(output).write_text(json_str)
                    click.secho(f"✓ Performance analysis saved to {output}", fg='green')
                else:
                    click.echo(json_str)
            else:
                lines = []
                lines.append(f"\n🚀 Performance Analysis for Query: {query}")
                lines.append(f"Experiment ID: {experiment_id}")
                lines.append(f"Runs Analyzed: {result['runs']}")
                lines.append("")
                lines.append("Execution Time:")
                for metric, value in result['execution_time'].items():
                    if isinstance(value, float):
                        lines.append(f"  {metric}: {value:.3f}s")
                    else:
                        lines.append(f"  {metric}: {value}")
                
                if 'throughput' in result:
                    lines.append("\nThroughput:")
                    for metric, value in result['throughput'].items():
                        lines.append(f"  {metric}: {value:.2f}")
                
                lines.append("")
                text_output = '\n'.join(lines)
                
                if output:
                    Path(output).write_text(text_output)
                    click.secho(f"✓ Performance analysis saved to {output}", fg='green')
                else:
                    click.echo(text_output)
        
        else:
            # Analyze entire experiment
            result = analyzer.analyze_experiment_performance(
                experiment_id,
                group_by_query=breakdown
            )
            
            if output_format == 'json':
                json_str = json.dumps(result, indent=2)
                if output:
                    Path(output).write_text(json_str)
                    click.secho(f"✓ Performance analysis saved to {output}", fg='green')
                else:
                    click.echo(json_str)
            else:
                lines = []
                lines.append(f"\n🚀 Performance Analysis for Experiment {experiment_id}")
                lines.append(f"Total Runs: {result['total_runs']}")
                if 'total_queries_executed' in result:
                    lines.append(f"Total Queries Executed: {result['total_queries_executed']}")
                lines.append("")
                
                if 'overall_execution_time' in result:
                    lines.append("Overall Execution Time Statistics:")
                    for key, val in result['overall_execution_time'].items():
                        if isinstance(val, float):
                            lines.append(f"  {key}: {val:.3f}s")
                        else:
                            lines.append(f"  {key}: {val}")
                
                if 'average_throughput_qps' in result:
                    lines.append(f"\nAverage Throughput: {result['average_throughput_qps']:.2f} queries/sec")
                
                if breakdown and 'per_query_statistics' in result:
                    lines.append("\nPer-Query Statistics:")
                    for qname, stats in result['per_query_statistics'].items():
                        lines.append(f"\n  {qname}:")
                        lines.append(f"    Count:  {stats['count']}")
                        lines.append(f"    Mean:   {stats['mean']:.3f}s")
                        lines.append(f"    Median: {stats['median']:.3f}s")
                        lines.append(f"    Min:    {stats['min']:.3f}s")
                        lines.append(f"    Max:    {stats['max']:.3f}s")
                
                lines.append("")
                text_output = '\n'.join(lines)
                
                if output:
                    Path(output).write_text(text_output)
                    click.secho(f"✓ Performance analysis saved to {output}", fg='green')
                else:
                    click.echo(text_output)
    
    except Exception as e:
        click.secho(f"✗ Performance analysis failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@analyze_group.command(name="compare")
@click.argument("baseline_id", type=int)
@click.argument("current_id", type=int)
@click.option('--query', help='Compare specific query only.')
@click.option('--significance', type=float, default=0.05,
              help='Statistical significance level (default: 0.05).')
@click.option('--format', 'output_format', 
              type=click.Choice(['text', 'json']),
              default='text',
              help='Output format.')
@click.option('--output', type=click.Path(), help='Save comparison to file.')
@verbose_option
@click.pass_context
def analyze_compare(ctx, baseline_id, current_id, query, significance, output_format, output, verbose):
    """Compare two experiments (baseline vs current).
    
    Performs statistical comparison using t-tests to determine if
    performance differences are statistically significant.
    
    \b
    Examples:
        tribench res analyze compare 1 2
        tribench res analyze compare 1 2 --query "Q1"
        tribench res analyze compare 1 2 --significance 0.01 --format json
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if not STORAGE_AVAILABLE or not ANALYSIS_AVAILABLE:
        click.secho("✗ Analysis requires storage and analysis modules", fg='red')
        return
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        analyzer = ComparisonAnalyzer(result_storage=storage)
        
        result = analyzer.compare_experiments(
            baseline_id,
            current_id,
            significance_level=significance
        )
        
        if output_format == 'json':
            json_str = json.dumps(result, indent=2)
            if output:
                Path(output).write_text(json_str)
                click.secho(f"✓ Comparison saved to {output}", fg='green')
            else:
                click.echo(json_str)
        else:
            lines = []
            lines.append(f"\n📊 Experiment Comparison")
            lines.append(f"Baseline: {result['baseline']['name']} (ID: {baseline_id})")
            lines.append(f"Current:  {result['current']['name']} (ID: {current_id})")
            lines.append(f"Significance Level: {significance}")
            lines.append("")
            lines.append("Summary:")
            lines.append(f"  Improvements:  {result['summary']['improvements']}")
            lines.append(f"  Regressions:   {result['summary']['regressions']}")
            lines.append(f"  No Change:     {result['summary']['no_significant_change']}")
            overall_change = result['summary'].get('overall_performance_change', {})
            if 'percent_change' in overall_change:
                lines.append(f"  Overall:       {overall_change['percent_change']:.2f}% change")
            
            if query:
                # Show details for specific query
                if query in result['comparisons']:
                    comp = result['comparisons'][query]
                    lines.append(f"\nQuery: {query}")
                    lines.append(f"  Baseline Mean:  {comp['baseline']['mean']:.3f}s")
                    lines.append(f"  Current Mean:   {comp['current']['mean']:.3f}s")
                    lines.append(f"  Change:         {comp['difference']['percent_change']:.2f}%")
                    lines.append(f"  Verdict:        {comp['verdict']['status'].upper()}")
                    lines.append(f"  Significant:    {'Yes' if comp['statistical_test']['is_significant'] else 'No'}")
                    if comp['statistical_test']['is_significant']:
                        lines.append(f"  p-value:        {comp['statistical_test']['p_value']:.4f}")
            else:
                # Show all query comparisons
                lines.append("\nQuery-Level Results:")
                for qname, comp in sorted(result['comparisons'].items()):
                    status = comp['verdict']['status']
                    verdict_icon = "🟢" if status == 'improvement' else "🔴" if status == 'regression' else "⚪"
                    sig_mark = "*" if comp['statistical_test']['is_significant'] else ""
                    lines.append(f"  {verdict_icon} {qname}: {comp['difference']['percent_change']:+.2f}% {status}{sig_mark}")
            
            lines.append("")
            lines.append("Legend: * = statistically significant")
            lines.append("")
            
            text_output = '\n'.join(lines)
            
            if output:
                Path(output).write_text(text_output)
                click.secho(f"✓ Comparison saved to {output}", fg='green')
            else:
                click.echo(text_output)
    
    except Exception as e:
        click.secho(f"✗ Comparison failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@analyze_group.command(name="scalability")
@click.argument("baseline_id", type=int)
@click.argument("scaled_id", type=int)
@click.option('--baseline-workers', type=int, default=1,
              help='Number of workers in baseline (default: 1).')
@click.option('--scaled-workers', type=int, required=True,
              help='Number of workers in scaled configuration.')
@click.option('--format', 'output_format', 
              type=click.Choice(['text', 'json']),
              default='text',
              help='Output format.')
@click.option('--output', type=click.Path(), help='Save analysis to file.')
@verbose_option
@click.pass_context
def analyze_scalability(ctx, baseline_id, scaled_id, baseline_workers, scaled_workers, 
                        output_format, output, verbose):
    """Analyze scalability (speed-up and efficiency).
    
    Calculates speed-up and efficiency metrics when scaling from baseline
    to scaled worker configuration.
    
    \b
    Examples:
        tribench res analyze scalability 1 2 --scaled-workers 4
        tribench res analyze scalability 1 2 --baseline-workers 1 --scaled-workers 8
        tribench res analyze scalability 1 2 --scaled-workers 4 --format json
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if not STORAGE_AVAILABLE or not ANALYSIS_AVAILABLE:
        click.secho("✗ Analysis requires storage and analysis modules", fg='red')
        return
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        analyzer = ScalabilityAnalyzer(result_storage=storage)
        
        result = analyzer.calculate_speedup(
            baseline_experiment_id=baseline_id,
            scaled_experiment_id=scaled_id,
            baseline_workers=baseline_workers,
            scaled_workers=scaled_workers
        )
        
        if output_format == 'json':
            json_str = json.dumps(result, indent=2)
            if output:
                Path(output).write_text(json_str)
                click.secho(f"✓ Scalability analysis saved to {output}", fg='green')
            else:
                click.echo(json_str)
        else:
            lines = []
            lines.append(f"\n📈 Scalability Analysis")
            lines.append(f"Baseline: Experiment {baseline_id} - {baseline_workers} worker(s)")
            lines.append(f"Scaled:   Experiment {scaled_id} - {scaled_workers} worker(s)")
            lines.append("")
            
            if 'overall' in result:
                lines.append("Overall Metrics:")
                overall = result['overall']
                lines.append(f"  Average Speed-up: {overall['average_speedup']:.2f}x")
                lines.append(f"  Median Speed-up:  {overall['median_speedup']:.2f}x")
                lines.append(f"  Min Speed-up:     {overall['min_speedup']:.2f}x")
                lines.append(f"  Max Speed-up:     {overall['max_speedup']:.2f}x")
                
                if 'average_efficiency_percent' in overall:
                    lines.append(f"  Average Efficiency: {overall['average_efficiency_percent']:.1f}%")
                    lines.append(f"  Ideal Speed-up:     {overall['ideal_speedup']:.2f}x")
                    
                    # Classify efficiency
                    eff = overall['average_efficiency_percent']
                    if eff >= 90:
                        efficiency_verdict = "Excellent (near-linear scaling)"
                    elif eff >= 70:
                        efficiency_verdict = "Good"
                    elif eff >= 50:
                        efficiency_verdict = "Fair"
                    else:
                        efficiency_verdict = "Poor"
                    lines.append(f"  Assessment:         {efficiency_verdict}")
                lines.append("")
            
            if 'query_speedups' in result and result['query_speedups']:
                lines.append("Per-Query Speed-up:")
                for qname in sorted(result['query_speedups'].keys()):
                    qdata = result['query_speedups'][qname]
                    speedup_icon = "🚀" if qdata['speedup'] > 1.0 else "🐌"
                    lines.append(f"  {speedup_icon} {qname}:")
                    lines.append(f"      Baseline: {qdata['baseline_mean_time']:.3f}s")
                    lines.append(f"      Scaled:   {qdata['scaled_mean_time']:.3f}s")
                    lines.append(f"      Speed-up: {qdata['speedup']:.2f}x")
                    if qdata['efficiency_percent'] is not None:
                        lines.append(f"      Efficiency: {qdata['efficiency_percent']:.1f}%")
                lines.append("")
            
            lines.append("")
            text_output = '\n'.join(lines)
            
            if output:
                Path(output).write_text(text_output)
                click.secho(f"✓ Scalability analysis saved to {output}", fg='green')
            else:
                click.echo(text_output)
    
    except Exception as e:
        click.secho(f"✗ Scalability analysis failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


@analyze_group.command(name="regression")
@click.argument("baseline_id", type=int)
@click.argument("current_id", type=int)
@click.option('--threshold', type=float, default=5.0,
              help='Regression threshold percentage (default: 5.0).')
@click.option('--significance', type=float, default=0.05,
              help='Statistical significance level (default: 0.05).')
@click.option('--format', 'output_format', 
              type=click.Choice(['text', 'json']),
              default='text',
              help='Output format.')
@click.option('--output', type=click.Path(), help='Save report to file.')
@verbose_option
@click.pass_context
def analyze_regression(ctx, baseline_id, current_id, threshold, significance, 
                       output_format, output, verbose):
    """Detect performance regressions.
    
    Identifies queries where performance has degraded beyond the specified
    threshold with statistical significance.
    
    \b
    Examples:
        tribench res analyze regression 1 2
        tribench res analyze regression 1 2 --threshold 10.0
        tribench res analyze regression 1 2 --threshold 5.0 --significance 0.01
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if not STORAGE_AVAILABLE or not ANALYSIS_AVAILABLE:
        click.secho("✗ Analysis requires storage and analysis modules", fg='red')
        return
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        detector = RegressionDetector(result_storage=storage)
        
        result = detector.detect_regression(
            baseline_experiment_id=baseline_id,
            current_experiment_id=current_id,
            threshold_percent=threshold,
            significance_level=significance
        )
        
        if output_format == 'json':
            json_str = json.dumps(result, indent=2)
            if output:
                Path(output).write_text(json_str)
                click.secho(f"✓ Regression report saved to {output}", fg='green')
            else:
                click.echo(json_str)
        else:
            lines = []
            lines.append(f"\n🔍 Performance Regression Detection")
            lines.append(f"Baseline: Experiment {baseline_id}")
            lines.append(f"Current:  Experiment {current_id}")
            lines.append(f"Threshold: ≥{threshold}% slowdown")
            lines.append(f"Significance Level: {significance}")
            lines.append("")
            
            summary = result.get('summary', {})
            regressions_detected = summary.get('regression_detected', False)
            regressions_count = summary.get('regressions_count', 0)
            
            if regressions_detected:
                lines.append(f"⚠️  {regressions_count} Regression(s) Detected:")
                lines.append("")
                
                for reg in result.get('regressions', []):
                    # Severity indicators
                    severity = reg.get('severity', 'minor')
                    if severity == 'critical':
                        severity_icon = "🔴"
                    elif severity == 'major':
                        severity_icon = "🟠"
                    elif severity == 'moderate':
                        severity_icon = "🟡"
                    else:
                        severity_icon = "🟢"
                    
                    lines.append(f"{severity_icon} {reg['query_name']} [{severity.upper()}]")
                    lines.append(f"    Baseline:  {reg['baseline_mean']:.3f}s")
                    lines.append(f"    Current:   {reg['current_mean']:.3f}s")
                    lines.append(f"    Slowdown:  {reg['percent_change']:.2f}%")
                    if reg['is_statistically_significant']:
                        lines.append(f"    Significant: Yes")
                    lines.append("")
            else:
                lines.append(f"✓ No regressions detected (threshold: {threshold}%)")
            
            # Show improvements if any
            improvements = result.get('improvements', [])
            if improvements:
                lines.append(f"\n✨ {len(improvements)} Performance Improvement(s):")
                lines.append("")
                for imp in improvements[:5]:  # Show top 5
                    lines.append(f"  ✓ {imp['query_name']}")
                    lines.append(f"      Faster by: {abs(imp['percent_change']):.2f}%")
                if len(improvements) > 5:
                    lines.append(f"  ... and {len(improvements) - 5} more")
                lines.append("")
            
            # Summary
            lines.append("Summary:")
            lines.append(f"  Total Queries:  {summary.get('total_queries', 0)}")
            lines.append(f"  Regressions:    {regressions_count}")
            lines.append(f"  Improvements:   {summary.get('improvements_count', 0)}")
            lines.append(f"  No Change:      {summary.get('no_change_count', 0)}")
            lines.append("")
            
            lines.append("")
            text_output = '\n'.join(lines)
            
            if output:
                Path(output).write_text(text_output)
                click.secho(f"✓ Regression report saved to {output}", fg='green')
            else:
                click.echo(text_output)
                
                # Return exit code based on regression detection
                summary = result.get('summary', {})
                if summary.get('regression_detected', False):
                    ctx.exit(1)
    
    except Exception as e:
        click.secho(f"✗ Regression detection failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


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
        
        click.secho(f"✓ Deleted experiment: {experiment['name']} (ID: {experiment['id']})", fg='green')
        
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
