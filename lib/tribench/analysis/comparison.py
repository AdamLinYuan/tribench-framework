"""Comparison analysis for benchmark results."""

import logging
from typing import Dict, Any, List, Optional
from .statistical import StatisticalAnalyzer

logger = logging.getLogger(__name__)

class ComparisonAnalyzer:
    """
    Compares benchmark results         # Get all experiments
        experiments = []
        for exp_id in experiment_ids:
            exp = self.result_storage.get_experiment_by_id(exp_id)
            if exp:
                experiments.append({
                    "id": exp_id,
                    "name": exp.name if hasattr(exp, 'name') else exp.get('name'),
                    "type": exp.experiment_type if hasattr(exp, 'experiment_type') else exp.get('experiment_type'),
                })periments.
    
    Supports:
    - Baseline vs current comparisons
    - Multi-experiment comparisons
    - Statistical significance testing
    - Performance regression detection
    """
    
    def __init__(self, result_storage=None):
        """
        Initialize comparison analyzer.
        
        Args:
            result_storage: Optional ResultStorage instance
        """
        self.result_storage = result_storage
        self.statistical = StatisticalAnalyzer()
    
    def compare_experiments(
        self,
        baseline_experiment_id: int,
        current_experiment_id: int,
        significance_level: float = 0.05
    ) -> Dict[str, Any]:
        """
        Compare two experiments (baseline vs current).
        
        Args:
            baseline_experiment_id: Baseline experiment ID
            current_experiment_id: Current experiment ID
            significance_level: Significance level for statistical tests (default 0.05)
            
        Returns:
            Comprehensive comparison results
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for experiment comparison")
        
        # Get both experiments
        baseline = self.result_storage.get_experiment_by_id(baseline_experiment_id)
        current = self.result_storage.get_experiment_by_id(current_experiment_id)
        
        if not baseline:
            return {"error": f"Baseline experiment {baseline_experiment_id} not found"}
        if not current:
            return {"error": f"Current experiment {current_experiment_id} not found"}
        
        result = {
            "baseline": {
                "experiment_id": baseline_experiment_id,
                "name": baseline['name'],
                "type": baseline['experiment_type'],
            },
            "current": {
                "experiment_id": current_experiment_id,
                "name": current['name'],
                "type": current['experiment_type'],
            },
            "comparisons": {}
        }
        
        # Get all runs for both experiments
        baseline_runs = self.result_storage.get_experiment_runs(baseline_experiment_id)
        current_runs = self.result_storage.get_experiment_runs(current_experiment_id)
        
        # Collect query-level data
        baseline_queries = self._collect_query_data(baseline_runs)
        current_queries = self._collect_query_data(current_runs)
        
        # Find common queries
        common_queries = set(baseline_queries.keys()) & set(current_queries.keys())
        
        if not common_queries:
            return {**result, "error": "No common queries found between experiments"}
        
        # Compare each query
        query_comparisons = {}
        overall_improvements = []
        overall_regressions = []
        
        for query_name in common_queries:
            baseline_times = baseline_queries[query_name]
            current_times = current_queries[query_name]
            
            comparison = self._compare_query_times(
                query_name,
                baseline_times,
                current_times,
                significance_level
            )
            
            query_comparisons[query_name] = comparison
            
            # Track improvements and regressions
            if comparison['verdict']['is_regression']:
                overall_regressions.append(query_name)
            elif comparison['verdict']['is_improvement']:
                overall_improvements.append(query_name)
        
        result["comparisons"] = query_comparisons
        result["summary"] = {
            "total_queries_compared": len(common_queries),
            "improvements": len(overall_improvements),
            "regressions": len(overall_regressions),
            "no_significant_change": len(common_queries) - len(overall_improvements) - len(overall_regressions),
            "improved_queries": overall_improvements,
            "regressed_queries": overall_regressions,
        }
        
        # Overall performance change
        all_baseline_times = [t for times in baseline_queries.values() for t in times]
        all_current_times = [t for times in current_queries.values() for t in times]
        
        if all_baseline_times and all_current_times:
            baseline_mean = sum(all_baseline_times) / len(all_baseline_times)
            current_mean = sum(all_current_times) / len(all_current_times)
            percent_change = ((current_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0
            
            result["summary"]["overall_performance_change"] = {
                "baseline_mean_time": baseline_mean,
                "current_mean_time": current_mean,
                "percent_change": percent_change,
                "is_faster": current_mean < baseline_mean,
            }
        
        return result
    
    def _collect_query_data(self, runs: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """
        Collect query execution times from runs.
        
        Args:
            runs: List of run dictionaries
            
        Returns:
            Dictionary mapping query names to lists of execution times
        """
        query_data = {}
        
        for run in runs:
            if run['status'] != 'completed':
                continue
            
            executions = self.result_storage.get_run_query_executions(run['id'])
            
            for execution in executions:
                if execution['status'] == 'completed' and execution['execution_time']:
                    query_name = execution['query_name']
                    if query_name not in query_data:
                        query_data[query_name] = []
                    query_data[query_name].append(execution['execution_time'])
        
        return query_data
    
    def _compare_query_times(
        self,
        query_name: str,
        baseline_times: List[float],
        current_times: List[float],
        significance_level: float
    ) -> Dict[str, Any]:
        """
        Compare query execution times with statistical significance testing.
        
        Args:
            query_name: Name of the query
            baseline_times: Baseline execution times
            current_times: Current execution times
            significance_level: Significance level for t-test
            
        Returns:
            Comparison results with statistical significance
        """
        baseline_stats = self.statistical.calculate_statistics(baseline_times)
        current_stats = self.statistical.calculate_statistics(current_times)
        
        # Calculate difference
        mean_diff = current_stats['mean'] - baseline_stats['mean']
        percent_change = (mean_diff / baseline_stats['mean'] * 100) if baseline_stats['mean'] > 0 else 0
        
        # Perform t-test for statistical significance
        from scipy import stats as scipy_stats
        t_statistic, p_value = scipy_stats.ttest_ind(baseline_times, current_times)
        is_significant = bool(p_value < significance_level)  # Convert numpy bool to Python bool
        
        # Determine if it's an improvement or regression
        is_faster = current_stats['mean'] < baseline_stats['mean']
        is_improvement = is_faster and is_significant
        is_regression = not is_faster and is_significant
        
        return {
            "query_name": query_name,
            "baseline": {
                "mean": float(baseline_stats['mean']),
                "median": float(baseline_stats['median']),
                "stdev": float(baseline_stats['stdev']),
                "min": float(baseline_stats['min']),
                "max": float(baseline_stats['max']),
                "count": int(baseline_stats['count']),
            },
            "current": {
                "mean": float(current_stats['mean']),
                "median": float(current_stats['median']),
                "stdev": float(current_stats['stdev']),
                "min": float(current_stats['min']),
                "max": float(current_stats['max']),
                "count": int(current_stats['count']),
            },
            "difference": {
                "mean_diff_seconds": float(mean_diff),
                "percent_change": float(percent_change),
                "median_diff_seconds": float(current_stats['median'] - baseline_stats['median']),
            },
            "statistical_test": {
                "t_statistic": float(t_statistic),
                "p_value": float(p_value),
                "is_significant": is_significant,
                "significance_level": float(significance_level),
            },
            "verdict": {
                "is_faster": bool(is_faster),
                "is_improvement": bool(is_improvement),
                "is_regression": bool(is_regression),
                "status": "improvement" if is_improvement else ("regression" if is_regression else "no_change"),
            }
        }
    
    def compare_multiple_experiments(
        self,
        experiment_ids: List[int],
        query_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple experiments.
        
        Args:
            experiment_ids: List of experiment IDs to compare
            query_name: Optional specific query to compare (if None, compares all common queries)
            
        Returns:
            Multi-experiment comparison results
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for multi-experiment comparison")
        
        if len(experiment_ids) < 2:
            return {"error": "Need at least 2 experiments to compare"}
        
        # Get all experiments
        experiments = []
        for exp_id in experiment_ids:
            exp = self.result_storage.get_experiment_by_id(exp_id)
            if exp:
                experiments.append({
                    "id": exp_id,
                    "name": exp['name'],
                    "type": exp['experiment_type'],
                })
        
        if len(experiments) < 2:
            return {"error": "Could not find at least 2 valid experiments"}
        
        result = {
            "experiments": experiments,
            "query_comparisons": {}
        }
        
        # Collect query data for all experiments
        all_query_data = {}
        for exp_id in experiment_ids:
            runs = self.result_storage.get_experiment_runs(exp_id)
            all_query_data[exp_id] = self._collect_query_data(runs)
        
        # Find common queries across all experiments
        query_sets = [set(data.keys()) for data in all_query_data.values()]
        common_queries = set.intersection(*query_sets) if query_sets else set()
        
        if query_name:
            # Filter to specific query
            if query_name in common_queries:
                common_queries = {query_name}
            else:
                return {"error": f"Query '{query_name}' not found in all experiments"}
        
        # Compare each common query across all experiments
        for qname in common_queries:
            query_comparison = {
                "query_name": qname,
                "experiment_stats": {}
            }
            
            for exp_id in experiment_ids:
                times = all_query_data[exp_id][qname]
                stats = self.statistical.calculate_statistics(times)
                query_comparison["experiment_stats"][exp_id] = {
                    "mean": stats['mean'],
                    "median": stats['median'],
                    "stdev": stats['stdev'],
                    "min": stats['min'],
                    "max": stats['max'],
                }
            
            # Find fastest and slowest
            means = {exp_id: data['mean'] for exp_id, data in query_comparison["experiment_stats"].items()}
            fastest_exp = min(means, key=means.get)
            slowest_exp = max(means, key=means.get)
            
            query_comparison["fastest_experiment"] = fastest_exp
            query_comparison["slowest_experiment"] = slowest_exp
            query_comparison["speed_difference_percent"] = (
                (means[slowest_exp] - means[fastest_exp]) / means[fastest_exp] * 100
                if means[fastest_exp] > 0 else 0
            )
            
            result["query_comparisons"][qname] = query_comparison
        
        return result
