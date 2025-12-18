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
