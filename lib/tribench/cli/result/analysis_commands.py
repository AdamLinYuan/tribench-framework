"""
Result analysis commands.

Advanced analysis commands using statistical and performance analyzers.
"""

import click
import json
from pathlib import Path
from tribench.cli.base import verbose_option
from .utils import get_storage, STORAGE_AVAILABLE, ANALYSIS_AVAILABLE

# Import analysis modules for type hints
if ANALYSIS_AVAILABLE:
    from tribench.analysis import (
        StatisticalAnalyzer,
        PerformanceAnalyzer,
        ComparisonAnalyzer,
        ScalabilityAnalyzer,
        RegressionDetector,
    )


@click.group(name="analyze")
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
        click.secho("Error: Analysis requires storage and analysis modules", fg='red')
        return
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        # Get experiment
        experiment = storage.get_experiment_by_id(experiment_id)
        if not experiment:
            click.secho(f"Error: Experiment {experiment_id} not found", fg='red')
            return
        
        # Get runs
        runs = storage.get_experiment_runs(experiment_id)
        if not runs:
            click.secho(f"Error: No runs found for experiment {experiment_id}", fg='red')
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
            click.secho(f"Error: No query executions found", fg='red')
            return
        
        # Filter by query if specified
        if query:
            all_executions = [e for e in all_executions if e['query_name'] == query]
            if not all_executions:
                click.secho(f"Error: No executions found for query {query}", fg='red')
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
                click.secho(f"Statistics saved to {output}", fg='green')
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
                click.secho(f"Statistics saved to {output}", fg='green')
            else:
                click.echo(csv_str)
        
        else:  # text format
            lines = []
            lines.append(f"\nStatistical Analysis for Experiment {experiment_id}: {experiment['name']}")
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
                click.secho(f"Statistics saved to {output}", fg='green')
            else:
                click.echo(text_output)
    
    except Exception as e:
        click.secho(f"Error: Analysis failed: {e}", fg='red')
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
        click.secho("Error: Analysis requires storage and analysis modules", fg='red')
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
                    click.secho(f"Performance analysis saved to {output}", fg='green')
                else:
                    click.echo(json_str)
            else:
                lines = []
                lines.append(f"\nPerformance Analysis for Query: {query}")
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
                    click.secho(f"Performance analysis saved to {output}", fg='green')
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
                    click.secho(f"Performance analysis saved to {output}", fg='green')
                else:
                    click.echo(json_str)
            else:
                lines = []
                lines.append(f"\nPerformance Analysis for Experiment {experiment_id}")
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
                    click.secho(f"Performance analysis saved to {output}", fg='green')
                else:
                    click.echo(text_output)
    
    except Exception as e:
        click.secho(f"Error: Performance analysis failed: {e}", fg='red')
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
    performance differences are statistically significant. Shows comprehensive
    performance statistics, per-query breakdowns, and monitoring metrics.
    
    \b
    Examples:
        tribench res analyze compare 1 2
        tribench res analyze compare 1 2 --query "Q1"
        tribench res analyze compare 1 2 --significance 0.01 --format json
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if not STORAGE_AVAILABLE or not ANALYSIS_AVAILABLE:
        click.secho("Error: Analysis requires storage and analysis modules", fg='red')
        return
    
    storage = get_storage()
    if not storage:
        return
    
    try:
        # Get performance analysis for both experiments
        perf_analyzer = PerformanceAnalyzer(storage=storage)
        baseline_perf = perf_analyzer.analyze_experiment_performance(baseline_id, group_by_query=True)
        current_perf = perf_analyzer.analyze_experiment_performance(current_id, group_by_query=True)
        
        # Get comparison analysis
        comp_analyzer = ComparisonAnalyzer(result_storage=storage)
        result = comp_analyzer.compare_experiments(
            baseline_id,
            current_id,
            significance_level=significance
        )
        
        # Get monitoring metrics for both experiments
        baseline_runs = storage.get_experiment_runs(baseline_id)
        current_runs = storage.get_experiment_runs(current_id)
        baseline_monitoring = _aggregate_experiment_monitoring(storage, baseline_runs)
        current_monitoring = _aggregate_experiment_monitoring(storage, current_runs)
        
        if output_format == 'json':
            # Include all data in JSON output
            result['baseline_performance'] = baseline_perf
            result['current_performance'] = current_perf
            result['baseline_monitoring'] = baseline_monitoring
            result['current_monitoring'] = current_monitoring
            
            json_str = json.dumps(result, indent=2)
            if output:
                Path(output).write_text(json_str)
                click.secho(f"Comparison saved to {output}", fg='green')
            else:
                click.echo(json_str)
        else:
            lines = []
            lines.append(f"\n{'='*90}")
            lines.append(f"COMPREHENSIVE EXPERIMENT COMPARISON")
            lines.append(f"{'='*90}")
            lines.append(f"Baseline: {result['baseline']['name']} (ID: {baseline_id})")
            lines.append(f"Current:  {result['current']['name']} (ID: {current_id})")
            lines.append(f"Significance Level: {significance}")
            lines.append("")
            
            # Overall Performance Statistics Table
            lines.append("OVERALL PERFORMANCE STATISTICS")
            lines.append("="*90)
            lines.extend(_format_performance_comparison_table(baseline_perf, current_perf, baseline_runs, current_runs))
            lines.append("")
            
            # Per-Query Comparison Table
            if not query and 'per_query_statistics' in baseline_perf and 'per_query_statistics' in current_perf:
                lines.append("PER-QUERY PERFORMANCE COMPARISON")
                lines.append("="*90)
                lines.extend(_format_query_comparison_table(
                    baseline_perf['per_query_statistics'],
                    current_perf['per_query_statistics'],
                    result['comparisons']
                ))
                lines.append("")
            elif query and query in result.get('comparisons', {}):
                comp = result['comparisons'][query]
                lines.append(f"QUERY PERFORMANCE: {query}")
                lines.append("="*90)
                lines.extend(_format_single_query_comparison(comp))
                lines.append("")
            
            # Monitoring Metrics Comparison
            if baseline_monitoring and current_monitoring:
                lines.append("MONITORING METRICS COMPARISON")
                lines.append("="*90)
                lines.extend(_format_monitoring_comparison_table(baseline_monitoring, current_monitoring))
                lines.append("")
            
            # Summary
            lines.append("SUMMARY")
            lines.append("="*90)
            lines.append(f"Queries Compared:      {result['summary']['total_queries_compared']}")
            lines.append(f"Improvements:          {result['summary']['improvements']} queries")
            lines.append(f"Regressions:           {result['summary']['regressions']} queries")
            lines.append(f"No Significant Change: {result['summary']['no_significant_change']} queries")
            
            overall_change = result['summary'].get('overall_performance_change', {})
            if 'percent_change' in overall_change:
                direction = "(faster)" if overall_change['is_faster'] else "(slower)"
                lines.append(f"Overall Change:        {overall_change['percent_change']:+.2f}% {direction}")
            
            lines.append("")
            lines.append("="*90)
            lines.append("")
            
            text_output = '\n'.join(lines)
            
            if output:
                Path(output).write_text(text_output)
                click.secho(f"Comparison saved to {output}", fg='green')
            else:
                click.echo(text_output)
    
    except Exception as e:
        click.secho(f"Error: Comparison failed: {e}", fg='red')
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
        click.secho("Error: Analysis requires storage and analysis modules", fg='red')
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
                click.secho(f"Scalability analysis saved to {output}", fg='green')
            else:
                click.echo(json_str)
        else:
            lines = []
            lines.append(f"\nScalability Analysis")
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
                    speedup_text = "speedup" if qdata['speedup'] > 1.0 else "slowdown"
                    lines.append(f"  [{speedup_text}] {qname}:")
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
                click.secho(f"Scalability analysis saved to {output}", fg='green')
            else:
                click.echo(text_output)
    
    except Exception as e:
        click.secho(f"Error: Scalability analysis failed: {e}", fg='red')
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
        click.secho("Error: Analysis requires storage and analysis modules", fg='red')
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
                click.secho(f"Regression report saved to {output}", fg='green')
            else:
                click.echo(json_str)
        else:
            lines = []
            lines.append(f"\nPerformance Regression Detection")
            lines.append(f"Baseline: Experiment {baseline_id}")
            lines.append(f"Current:  Experiment {current_id}")
            lines.append(f"Threshold: ≥{threshold}% slowdown")
            lines.append(f"Significance Level: {significance}")
            lines.append("")
            
            summary = result.get('summary', {})
            regressions_detected = summary.get('regression_detected', False)
            regressions_count = summary.get('regressions_count', 0)
            
            if regressions_detected:
                lines.append(f"WARNING: {regressions_count} Regression(s) Detected:")
                lines.append("")
                
                for reg in result.get('regressions', []):
                    # Severity indicators
                    severity = reg.get('severity', 'minor')
                    
                    lines.append(f"[{severity.upper()}] {reg['query_name']}")
                    lines.append(f"    Baseline:  {reg['baseline_mean']:.3f}s")
                    lines.append(f"    Current:   {reg['current_mean']:.3f}s")
                    lines.append(f"    Slowdown:  {reg['percent_change']:.2f}%")
                    if reg['is_statistically_significant']:
                        lines.append(f"    Significant: Yes")
                    lines.append("")
            else:
                lines.append(f"No regressions detected (threshold: {threshold}%)")
            
            # Show improvements if any
            improvements = result.get('improvements', [])
            if improvements:
                lines.append(f"\n{len(improvements)} Performance Improvement(s):")
                lines.append("")
                for imp in improvements[:5]:  # Show top 5
                    lines.append(f"  + {imp['query_name']}")
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
                click.secho(f"Regression report saved to {output}", fg='green')
            else:
                click.echo(text_output)
                
                # Return exit code based on regression detection
                summary = result.get('summary', {})
                if summary.get('regression_detected', False):
                    ctx.exit(1)
    
    except Exception as e:
        click.secho(f"Error: Regression detection failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())


# Helper functions for comprehensive comparison formatting

def _aggregate_experiment_monitoring(storage, runs):
    """Aggregate monitoring metrics across all runs in an experiment."""
    if not runs:
        return {}
    
    all_metrics = {}
    for run in runs:
        if run['status'] != 'completed':
            continue
        
        run_metrics = storage.get_monitoring_metrics_summary(run['id'])
        
        for metric_name, stats in run_metrics.items():
            if metric_name not in all_metrics:
                all_metrics[metric_name] = {
                    'counts': [],
                    'mins': [],
                    'maxs': [],
                    'means': []
                }
            
            all_metrics[metric_name]['counts'].append(stats['count'])
            if stats['min'] is not None:
                all_metrics[metric_name]['mins'].append(stats['min'])
            if stats['max'] is not None:
                all_metrics[metric_name]['maxs'].append(stats['max'])
            if stats['mean'] is not None:
                all_metrics[metric_name]['means'].append(stats['mean'])
    
    # Calculate aggregated statistics
    aggregated = {}
    for metric_name, data in all_metrics.items():
        aggregated[metric_name] = {
            'count': sum(data['counts']),
            'min': min(data['mins']) if data['mins'] else None,
            'max': max(data['maxs']) if data['maxs'] else None,
            'mean': sum(data['means']) / len(data['means']) if data['means'] else None,
        }
    
    return aggregated


def _format_performance_comparison_table(baseline_perf, current_perf, baseline_runs=None, current_runs=None):
    """Format overall performance statistics as a comparison table."""
    lines = []
    
    # Extract statistics
    baseline_stats = baseline_perf.get('overall_execution_time', {})
    current_stats = current_perf.get('overall_execution_time', {})
    
    # Calculate total runtime and query stats from runs if provided
    total_metrics = {}
    if baseline_runs and current_runs:
        baseline_duration = sum(r.get('duration_seconds', 0) for r in baseline_runs)
        current_duration = sum(r.get('duration_seconds', 0) for r in current_runs)
        baseline_queries = sum(r.get('queries_total', 0) for r in baseline_runs)
        current_queries = sum(r.get('queries_total', 0) for r in current_runs)
        baseline_success = sum(r.get('queries_succeeded', 0) for r in baseline_runs)
        current_success = sum(r.get('queries_succeeded', 0) for r in current_runs)
        
        total_metrics = {
            'total_runtime': (baseline_duration, current_duration),
            'total_queries': (baseline_queries, current_queries),
            'success_rate': (baseline_success / baseline_queries * 100 if baseline_queries > 0 else 0,
                           current_success / current_queries * 100 if current_queries > 0 else 0)
        }
    
    # Define metrics to compare
    metrics = ['count', 'mean', 'median', 'stdev', 'min', 'max', 'p50', 'p90', 'p95', 'p99']
    
    # Table header
    lines.append(f"{'Metric':<16} {'Baseline':<16} {'Current':<16} {'Difference':<16} {'% Change':<12}")
    lines.append("-" * 80)
    
    # Add total metrics first if available
    if total_metrics:
        # Total runtime
        if 'total_runtime' in total_metrics:
            baseline_val, current_val = total_metrics['total_runtime']
            diff = current_val - baseline_val
            pct_change = (diff / baseline_val * 100) if baseline_val != 0 else 0
            baseline_str = f"{baseline_val:.2f}s"
            current_str = f"{current_val:.2f}s"
            diff_str = f"{diff:+.2f}s"
            pct_str = f"{pct_change:+.2f}%"
            if pct_change < -5:
                pct_str = f"{pct_str} (better)"
            elif pct_change > 5:
                pct_str = f"{pct_str} (worse)"
            lines.append(f"{'total_runtime':<16} {baseline_str:<16} {current_str:<16} {diff_str:<16} {pct_str:<12}")
        
        # Total queries
        if 'total_queries' in total_metrics:
            baseline_val, current_val = total_metrics['total_queries']
            diff = current_val - baseline_val
            lines.append(f"{'total_queries':<16} {int(baseline_val):<16} {int(current_val):<16} {int(diff):+d}{'':<12} {'':12}")
        
        # Success rate
        if 'success_rate' in total_metrics:
            baseline_val, current_val = total_metrics['success_rate']
            diff = current_val - baseline_val
            baseline_str = f"{baseline_val:.1f}%"
            current_str = f"{current_val:.1f}%"
            diff_str = f"{diff:+.1f}pp"
            lines.append(f"{'success_rate':<16} {baseline_str:<16} {current_str:<16} {diff_str:<16} {'':12}")
        
        lines.append("-" * 80)
    
    for metric in metrics:
        baseline_val = baseline_stats.get(metric)
        current_val = current_stats.get(metric)
        
        if baseline_val is not None and current_val is not None:
            diff = current_val - baseline_val
            pct_change = (diff / baseline_val * 100) if baseline_val != 0 else 0
            
            # Format values
            if metric == 'count':
                baseline_str = f"{baseline_val}"
                current_str = f"{current_val}"
                diff_str = f"{diff:+.0f}"
            else:
                baseline_str = f"{baseline_val:.3f}s"
                current_str = f"{current_val:.3f}s"
                diff_str = f"{diff:+.3f}s"
            
            pct_str = f"{pct_change:+.2f}%"
            
            # Add text indicator for significant changes
            if metric != 'count' and pct_change < -5:  # Improvement (faster)
                pct_str = f"{pct_str} (better)"
            elif metric != 'count' and pct_change > 5:  # Regression (slower)
                pct_str = f"{pct_str} (worse)"
            
            lines.append(f"{metric:<16} {baseline_str:<16} {current_str:<16} {diff_str:<16} {pct_str:<12}")
    
    return lines


def _format_query_comparison_table(baseline_queries, current_queries, comparisons):
    """Format per-query performance comparison as a table."""
    lines = []
    
    # Get common queries
    common_queries = set(baseline_queries.keys()) & set(current_queries.keys())
    
    if not common_queries:
        return ["No common queries found"]
    
    # Table header
    lines.append(f"{'Query':<15} {'Baseline':<12} {'Current':<12} {'Diff':<12} {'% Change':<12} {'Verdict':<15}")
    lines.append("-" * 80)
    
    # Sort queries by name
    for query_name in sorted(common_queries):
        baseline_stats = baseline_queries[query_name]
        current_stats = current_queries[query_name]
        
        baseline_mean = baseline_stats['mean']
        current_mean = current_stats['mean']
        
        diff = current_mean - baseline_mean
        pct_change = (diff / baseline_mean * 100) if baseline_mean != 0 else 0
        
        # Get verdict from comparison
        comp = comparisons.get(query_name, {})
        verdict = comp.get('verdict', {})
        status = verdict.get('status', 'no_change')
        is_sig = comp.get('statistical_test', {}).get('is_significant', False)
        
        # Format verdict
        if status == 'improvement':
            verdict_text = "Faster"
        elif status == 'regression':
            verdict_text = "Slower"
        else:
            verdict_text = "No Change"
        
        sig_mark = "*" if is_sig else ""
        verdict_str = f"{verdict_text}{sig_mark}"
        
        lines.append(
            f"{query_name:<15} "
            f"{baseline_mean:>10.3f}s "
            f"{current_mean:>10.3f}s "
            f"{diff:>+10.3f}s "
            f"{pct_change:>+10.2f}% "
            f"{verdict_str:<15}"
        )
    
    return lines


def _format_single_query_comparison(comp):
    """Format detailed comparison for a single query."""
    lines = []
    
    baseline = comp['baseline']
    current = comp['current']
    diff = comp['difference']
    test = comp['statistical_test']
    verdict = comp['verdict']
    
    lines.append(f"{'Metric':<20} {'Baseline':<15} {'Current':<15} {'Difference':<15}")
    lines.append("-" * 65)
    lines.append(f"{'Mean':<20} {baseline['mean']:<14.3f}s {current['mean']:<14.3f}s {diff['mean_diff_seconds']:>+14.3f}s")
    lines.append(f"{'Median':<20} {baseline['median']:<14.3f}s {current['median']:<14.3f}s {diff['median_diff_seconds']:>+14.3f}s")
    lines.append(f"{'Std Dev':<20} {baseline['stdev']:<14.3f}s {current['stdev']:<14.3f}s {'':>15}")
    lines.append(f"{'Min':<20} {baseline['min']:<14.3f}s {current['min']:<14.3f}s {'':>15}")
    lines.append(f"{'Max':<20} {baseline['max']:<14.3f}s {current['max']:<14.3f}s {'':>15}")
    lines.append(f"{'Count':<20} {baseline['count']:<15} {current['count']:<15} {'':>15}")
    lines.append("")
    lines.append(f"Percent Change: {diff['percent_change']:+.2f}%")
    lines.append(f"Statistical Significance: {'Yes' if test['is_significant'] else 'No'} (p={test['p_value']:.4f})")
    lines.append(f"Verdict: {verdict['status'].upper()}")
    
    return lines


def _format_monitoring_comparison_table(baseline_monitoring, current_monitoring):
    """Format monitoring metrics comparison as a table."""
    lines = []
    
    # Get common metrics
    common_metrics = set(baseline_monitoring.keys()) & set(current_monitoring.keys())
    
    if not common_metrics:
        return ["No common monitoring metrics found"]
    
    # Filter to most important metrics
    priority_metrics = [
        'cpu_percent', 'cpu_percent_total', 'memory_percent', 'memory_used',
        'network_recv', 'network_sent', 'pod_cpu_cores', 'pod_memory_gb',
        'trino.query.data.input.rows', 'trino.query.data.output.rows'
    ]
    
    # Show priority metrics first, then others
    display_metrics = [m for m in priority_metrics if m in common_metrics]
    other_metrics = sorted([m for m in common_metrics if m not in priority_metrics])
    display_metrics.extend(other_metrics[:10])  # Limit total metrics
    
    # Table header
    lines.append(f"{'Metric':<35} {'Baseline':<15} {'Current':<15} {'% Change':<12}")
    lines.append("-" * 80)
    
    for metric_name in display_metrics:
        baseline_stats = baseline_monitoring[metric_name]
        current_stats = current_monitoring[metric_name]
        
        baseline_mean = baseline_stats.get('mean')
        current_mean = current_stats.get('mean')
        
        if baseline_mean is not None and current_mean is not None and baseline_mean != 0:
            pct_change = ((current_mean - baseline_mean) / baseline_mean * 100)
            
            # Format based on metric type
            if 'bytes' in metric_name.lower():
                baseline_str = f"{baseline_mean/1e9:.2f} GB"
                current_str = f"{current_mean/1e9:.2f} GB"
            elif 'gb' in metric_name.lower():
                baseline_str = f"{baseline_mean:.2f} GB"
                current_str = f"{current_mean:.2f} GB"
            elif 'mb' in metric_name.lower():
                baseline_str = f"{baseline_mean:.2f} MB"
                current_str = f"{current_mean:.2f} MB"
            elif 'percent' in metric_name.lower():
                baseline_str = f"{baseline_mean:.2f}%"
                current_str = f"{current_mean:.2f}%"
            else:
                baseline_str = f"{baseline_mean:.2f}"
                current_str = f"{current_mean:.2f}"
            
            pct_str = f"{pct_change:+.2f}%"
            
            # Truncate metric name if too long
            display_name = metric_name[:33] + '..' if len(metric_name) > 35 else metric_name
            lines.append(f"{display_name:<35} {baseline_str:<15} {current_str:<15} {pct_str:<12}")
    
    if len(common_metrics) > len(display_metrics):
        lines.append(f"... and {len(common_metrics) - len(display_metrics)} more metrics")
    
    return lines
