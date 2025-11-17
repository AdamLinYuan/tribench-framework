"""Statistical analysis functions for benchmark results."""

import logging
import statistics
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class StatisticalAnalyzer:
    """
    Provides statistical analysis methods for benchmark data.
    
    Calculates descriptive statistics including:
    - Central tendency: mean, median
    - Dispersion: standard deviation, variance
    - Range: min, max
    - Percentiles: quartiles, arbitrary percentiles
    - Coefficient of variation
    """
    
    @staticmethod
    def calculate_statistics(values: List[float]) -> Dict[str, float]:
        """
        Calculate comprehensive statistics for a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary containing statistical measures
            
        Raises:
            ValueError: If values list is empty
        """
        if not values:
            raise ValueError("Cannot calculate statistics for empty list")
        
        # Filter out None values
        valid_values = [v for v in values if v is not None]
        
        if not valid_values:
            raise ValueError("No valid values to analyze")
        
        # Sort for percentile calculations
        sorted_values = sorted(valid_values)
        n = len(sorted_values)
        
        # Basic statistics
        mean = statistics.mean(valid_values)
        median = statistics.median(sorted_values)
        
        # Dispersion metrics
        if n > 1:
            stdev = statistics.stdev(valid_values)
            variance = statistics.variance(valid_values)
            cv = (stdev / mean * 100) if mean > 0 else 0.0  # Coefficient of variation (%)
        else:
            stdev = 0.0
            variance = 0.0
            cv = 0.0
        
        # Range
        min_val = min(sorted_values)
        max_val = max(sorted_values)
        range_val = max_val - min_val
        
        # Percentiles
        p25 = np.percentile(sorted_values, 25)
        p50 = np.percentile(sorted_values, 50)  # Should equal median
        p75 = np.percentile(sorted_values, 75)
        p90 = np.percentile(sorted_values, 90)
        p95 = np.percentile(sorted_values, 95)
        p99 = np.percentile(sorted_values, 99)
        
        # Interquartile range
        iqr = p75 - p25
        
        return {
            "count": n,
            "mean": mean,
            "median": median,
            "stdev": stdev,
            "variance": variance,
            "cv": cv,  # Coefficient of variation
            "min": min_val,
            "max": max_val,
            "range": range_val,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p90": p90,
            "p95": p95,
            "p99": p99,
            "iqr": iqr,
        }
    
    @staticmethod
    def calculate_percentile(values: List[float], percentile: float) -> float:
        """
        Calculate a specific percentile.
        
        Args:
            values: List of numeric values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not values:
            raise ValueError("Cannot calculate percentile for empty list")
        
        if not 0 <= percentile <= 100:
            raise ValueError(f"Percentile must be between 0 and 100, got {percentile}")
        
        valid_values = [v for v in values if v is not None]
        return np.percentile(valid_values, percentile)
    
    @staticmethod
    def calculate_confidence_interval(
        values: List[float],
        confidence: float = 0.95
    ) -> Dict[str, float]:
        """
        Calculate confidence interval for the mean.
        
        Args:
            values: List of numeric values
            confidence: Confidence level (default 0.95 for 95% CI)
            
        Returns:
            Dictionary with mean, lower_bound, upper_bound, margin_of_error
        """
        if not values:
            raise ValueError("Cannot calculate confidence interval for empty list")
        
        valid_values = [v for v in values if v is not None]
        n = len(valid_values)
        
        if n < 2:
            mean = valid_values[0]
            return {
                "mean": mean,
                "lower_bound": mean,
                "upper_bound": mean,
                "margin_of_error": 0.0,
                "confidence": confidence,
            }
        
        mean = statistics.mean(valid_values)
        stdev = statistics.stdev(valid_values)
        
        # Use t-distribution for small samples
        from scipy import stats
        t_value = stats.t.ppf((1 + confidence) / 2, n - 1)
        margin_of_error = t_value * (stdev / np.sqrt(n))
        
        return {
            "mean": mean,
            "lower_bound": mean - margin_of_error,
            "upper_bound": mean + margin_of_error,
            "margin_of_error": margin_of_error,
            "confidence": confidence,
        }
    
    @staticmethod
    def detect_outliers(values: List[float], method: str = "iqr") -> Dict[str, Any]:
        """
        Detect outliers in the data.
        
        Args:
            values: List of numeric values
            method: Detection method ("iqr" or "zscore")
            
        Returns:
            Dictionary with outliers, outlier_indices, and thresholds
        """
        if not values:
            return {"outliers": [], "outlier_indices": [], "method": method}
        
        valid_values = [v for v in values if v is not None]
        
        if method == "iqr":
            # IQR method
            q1 = np.percentile(valid_values, 25)
            q3 = np.percentile(valid_values, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = [v for v in valid_values if v < lower_bound or v > upper_bound]
            outlier_indices = [i for i, v in enumerate(valid_values) if v < lower_bound or v > upper_bound]
            
            return {
                "outliers": outliers,
                "outlier_indices": outlier_indices,
                "method": "iqr",
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
            }
        
        elif method == "zscore":
            # Z-score method (values beyond 3 standard deviations)
            mean = statistics.mean(valid_values)
            stdev = statistics.stdev(valid_values) if len(valid_values) > 1 else 0
            
            if stdev == 0:
                return {"outliers": [], "outlier_indices": [], "method": "zscore"}
            
            z_scores = [(v - mean) / stdev for v in valid_values]
            outliers = [v for v, z in zip(valid_values, z_scores) if abs(z) > 3]
            outlier_indices = [i for i, z in enumerate(z_scores) if abs(z) > 3]
            
            return {
                "outliers": outliers,
                "outlier_indices": outlier_indices,
                "method": "zscore",
                "threshold": 3.0,
                "mean": mean,
                "stdev": stdev,
            }
        
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")
    
    @staticmethod
    def aggregate_query_statistics(query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate statistics across multiple query executions.
        
        Args:
            query_results: List of query result dictionaries with 'execution_time_seconds'
            
        Returns:
            Aggregated statistics dictionary
        """
        if not query_results:
            return {"error": "No results to analyze"}
        
        # Extract execution times
        execution_times = []
        for result in query_results:
            exec_time = result.get('execution_time_seconds')
            if exec_time is not None:
                execution_times.append(exec_time)
        
        if not execution_times:
            return {"error": "No valid execution times found"}
        
        # Calculate statistics
        stats = StatisticalAnalyzer.calculate_statistics(execution_times)
        
        # Add additional metadata
        stats['total_runs'] = len(query_results)
        stats['successful_runs'] = len(execution_times)
        stats['failed_runs'] = len(query_results) - len(execution_times)
        
        return stats
