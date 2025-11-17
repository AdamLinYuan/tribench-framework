"""Regression detection for performance analysis."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from .statistical import StatisticalAnalyzer

logger = logging.getLogger(__name__)


class RegressionDetector:
    """
    Detects performance regressions in benchmark results.
    
    Uses statistical methods to identify:
    - Significant performance degradations
    - Trend analysis over time
    - Threshold-based alerts
    """
    
    def __init__(self, result_storage=None):
        """
        Initialize regression detector.
        
        Args:
            result_storage: Optional ResultStorage instance
        """
        self.result_storage = result_storage
        self.statistical = StatisticalAnalyzer()
    
    def detect_regression(
        self,
        baseline_experiment_id: int,
        current_experiment_id: int,
        threshold_percent: float = 5.0,
        significance_level: float = 0.05
    ) -> Dict[str, Any]:
        """
        Detect performance regressions between baseline and current experiments.
        
        A regression is detected if:
        1. Current performance is slower than baseline by threshold_percent
        2. The difference is statistically significant
        
        Args:
            baseline_experiment_id: Baseline experiment ID
            current_experiment_id: Current experiment ID
            threshold_percent: Minimum percent slowdown to consider (default 5%)
            significance_level: Statistical significance level (default 0.05)
            
        Returns:
            Regression detection results
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for regression detection")
        
        result = {
            "baseline_experiment_id": baseline_experiment_id,
            "current_experiment_id": current_experiment_id,
            "threshold_percent": threshold_percent,
            "significance_level": significance_level,
            "regressions": [],
            "improvements": [],
            "no_change": []
        }
        
        # Get data for both experiments
        baseline_data = self._get_experiment_data(baseline_experiment_id)
        current_data = self._get_experiment_data(current_experiment_id)
        
        if not baseline_data or not current_data:
            return {**result, "error": "Could not retrieve experiment data"}
        
        # Find common queries
        common_queries = set(baseline_data.keys()) & set(current_data.keys())
        
        for query_name in common_queries:
            baseline_times = baseline_data[query_name]
            current_times = current_data[query_name]
            
            # Calculate statistics
            baseline_mean = sum(baseline_times) / len(baseline_times)
            current_mean = sum(current_times) / len(current_times)
            
            percent_change = ((current_mean - baseline_mean) / baseline_mean * 100) if baseline_mean > 0 else 0
            
            # Statistical significance test
            is_significant = self._is_statistically_significant(
                baseline_times,
                current_times,
                significance_level
            )
            
            # Classify result
            regression_info = {
                "query_name": query_name,
                "baseline_mean": float(baseline_mean),
                "current_mean": float(current_mean),
                "percent_change": float(percent_change),
                "is_statistically_significant": bool(is_significant),
            }
            
            if percent_change > threshold_percent and is_significant:
                # Performance regression (slower)
                regression_info["severity"] = self._classify_severity(percent_change)
                result["regressions"].append(regression_info)
            elif percent_change < -threshold_percent and is_significant:
                # Performance improvement (faster)
                result["improvements"].append(regression_info)
            else:
                # No significant change
                result["no_change"].append(regression_info)
        
        # Summary
        result["summary"] = {
            "total_queries": len(common_queries),
            "regressions_count": len(result["regressions"]),
            "improvements_count": len(result["improvements"]),
            "no_change_count": len(result["no_change"]),
            "regression_detected": len(result["regressions"]) > 0,
        }
        
        return result
    
    def detect_trend_regression(
        self,
        experiment_ids: List[int],
        query_name: Optional[str] = None,
        window_size: int = 3
    ) -> Dict[str, Any]:
        """
        Detect regressions by analyzing trends over multiple experiments.
        
        Args:
            experiment_ids: List of experiment IDs in chronological order
            query_name: Optional specific query to analyze
            window_size: Number of experiments to use for trend calculation
            
        Returns:
            Trend regression analysis
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for trend regression detection")
        
        if len(experiment_ids) < window_size:
            return {"error": f"Need at least {window_size} experiments for trend analysis"}
        
        result = {
            "experiment_ids": experiment_ids,
            "window_size": window_size,
            "trends": {}
        }
        
        # Collect data for all experiments
        all_data = []
        for exp_id in experiment_ids:
            data = self._get_experiment_data(exp_id)
            all_data.append({"experiment_id": exp_id, "data": data})
        
        # Find common queries
        query_sets = [set(item['data'].keys()) for item in all_data]
        common_queries = set.intersection(*query_sets) if query_sets else set()
        
        if query_name:
            if query_name in common_queries:
                common_queries = {query_name}
            else:
                return {**result, "error": f"Query '{query_name}' not found in all experiments"}
        
        # Analyze trend for each query
        for qname in common_queries:
            # Extract mean times for each experiment
            time_series = []
            for item in all_data:
                times = item['data'][qname]
                mean_time = sum(times) / len(times)
                time_series.append({
                    "experiment_id": item['experiment_id'],
                    "mean_time": mean_time
                })
            
            # Calculate trend
            trend_analysis = self._calculate_trend(time_series, window_size)
            result["trends"][qname] = trend_analysis
        
        return result
    
    def check_threshold_violation(
        self,
        experiment_id: int,
        max_execution_time: Optional[float] = None,
        max_mean_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Check if any queries violate threshold limits.
        
        Args:
            experiment_id: Experiment ID to check
            max_execution_time: Maximum allowed execution time for any single query
            max_mean_time: Maximum allowed mean execution time
            
        Returns:
            Threshold violation results
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for threshold checking")
        
        result = {
            "experiment_id": experiment_id,
            "max_execution_time": max_execution_time,
            "max_mean_time": max_mean_time,
            "violations": []
        }
        
        # Get experiment data
        runs = self.result_storage.get_experiment_runs(experiment_id)
        
        for run in runs:
            executions = self.result_storage.get_run_query_executions(run['id'])
            
            for execution in executions:
                if execution['status'] != 'completed':
                    continue
                
                exec_time = execution['execution_time']
                query_name = execution['query_name']
                
                violations = []
                
                # Check individual execution time
                if max_execution_time and exec_time > max_execution_time:
                    violations.append({
                        "type": "max_execution_time",
                        "threshold": max_execution_time,
                        "actual": exec_time,
                        "excess_percent": ((exec_time - max_execution_time) / max_execution_time * 100)
                    })
                
                if violations:
                    result["violations"].append({
                        "query_name": query_name,
                        "run_id": run['id'],
                        "execution_time": exec_time,
                        "violations": violations
                    })
        
        # Check mean times if threshold specified
        if max_mean_time:
            query_data = self._get_experiment_data(experiment_id)
            
            for query_name, times in query_data.items():
                mean_time = sum(times) / len(times)
                
                if mean_time > max_mean_time:
                    result["violations"].append({
                        "query_name": query_name,
                        "type": "mean_time",
                        "threshold": max_mean_time,
                        "actual": mean_time,
                        "excess_percent": ((mean_time - max_mean_time) / max_mean_time * 100)
                    })
        
        result["summary"] = {
            "total_violations": len(result["violations"]),
            "has_violations": len(result["violations"]) > 0
        }
        
        return result
    
    def _get_experiment_data(self, experiment_id: int) -> Dict[str, List[float]]:
        """Get query execution times for an experiment."""
        runs = self.result_storage.get_experiment_runs(experiment_id)
        query_times = {}
        
        for run in runs:
            if run['status'] != 'completed':
                continue
            
            executions = self.result_storage.get_run_query_executions(run['id'])
            
            for execution in executions:
                if execution['status'] == 'completed' and execution['execution_time']:
                    query_name = execution['query_name']
                    if query_name not in query_times:
                        query_times[query_name] = []
                    query_times[query_name].append(execution['execution_time'])
        
        return query_times
    
    def _is_statistically_significant(
        self,
        baseline_times: List[float],
        current_times: List[float],
        significance_level: float
    ) -> bool:
        """Test if the difference is statistically significant using t-test."""
        try:
            from scipy import stats
            _, p_value = stats.ttest_ind(baseline_times, current_times)
            return p_value < significance_level
        except Exception as e:
            logger.warning(f"Statistical test failed: {e}")
            return False
    
    def _classify_severity(self, percent_change: float) -> str:
        """Classify regression severity based on percent change."""
        if percent_change >= 50:
            return "critical"
        elif percent_change >= 25:
            return "major"
        elif percent_change >= 10:
            return "moderate"
        else:
            return "minor"
    
    def _calculate_trend(
        self,
        time_series: List[Dict[str, Any]],
        window_size: int
    ) -> Dict[str, Any]:
        """
        Calculate trend using moving average and linear regression.
        
        Args:
            time_series: List of dicts with 'experiment_id' and 'mean_time'
            window_size: Window size for moving average
            
        Returns:
            Trend analysis results
        """
        if len(time_series) < window_size:
            return {"error": "Not enough data for trend analysis"}
        
        # Calculate moving average
        moving_avg = []
        for i in range(len(time_series) - window_size + 1):
            window = time_series[i:i + window_size]
            avg = sum(item['mean_time'] for item in window) / window_size
            moving_avg.append(avg)
        
        # Simple linear regression on the time series
        n = len(time_series)
        x = list(range(n))  # Experiment indices
        y = [item['mean_time'] for item in time_series]
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Determine trend direction
        if slope > 0.01:  # Increasing (regression)
            trend_direction = "increasing"
        elif slope < -0.01:  # Decreasing (improvement)
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"
        
        return {
            "time_series": time_series,
            "moving_average": moving_avg,
            "linear_fit": {
                "slope": slope,
                "intercept": intercept,
            },
            "trend_direction": trend_direction,
            "is_regression": trend_direction == "increasing",
        }
