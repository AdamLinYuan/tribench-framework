"""Scalability analysis for distributed benchmarks."""

import logging
from typing import Dict, Any, List, Optional
from .statistical import StatisticalAnalyzer

logger = logging.getLogger(__name__)


class ScalabilityAnalyzer:
    """
    Analyzes scalability characteristics of distributed executions.
    
    Calculates:
    - Speed-up: Performance improvement with more workers
    - Scale-up: Ability to handle larger datasets with more resources
    - Efficiency: How effectively additional resources are utilized
    """
    
    def __init__(self, result_storage=None):
        """
        Initialize scalability analyzer.
        
        Args:
            result_storage: Optional ResultStorage instance
        """
        self.result_storage = result_storage
        self.statistical = StatisticalAnalyzer()
    
    def calculate_speedup(
        self,
        baseline_experiment_id: int,
        scaled_experiment_id: int,
        baseline_workers: int = 1,
        scaled_workers: int = None
    ) -> Dict[str, Any]:
        """
        Calculate speed-up ratio for scaled execution.
        
        Speed-up = T_baseline / T_scaled
        Ideal speed-up = number of additional workers
        Efficiency = (Actual speed-up / Ideal speed-up) * 100%
        
        Args:
            baseline_experiment_id: Baseline experiment (e.g., single-node)
            scaled_experiment_id: Scaled experiment (e.g., multi-node)
            baseline_workers: Number of workers in baseline (default 1)
            scaled_workers: Number of workers in scaled experiment
            
        Returns:
            Speed-up analysis results
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for scalability analysis")
        
        # Get baseline and scaled data
        baseline_data = self._get_experiment_execution_times(baseline_experiment_id)
        scaled_data = self._get_experiment_execution_times(scaled_experiment_id)
        
        if not baseline_data or not scaled_data:
            return {"error": "Could not retrieve experiment data"}
        
        result = {
            "baseline_experiment_id": baseline_experiment_id,
            "scaled_experiment_id": scaled_experiment_id,
            "baseline_workers": baseline_workers,
            "scaled_workers": scaled_workers,
            "query_speedups": {}
        }
        
        # Find common queries
        common_queries = set(baseline_data.keys()) & set(scaled_data.keys())
        
        if not common_queries:
            return {**result, "error": "No common queries found"}
        
        # Calculate speed-up for each query
        speedups = []
        efficiencies = []
        
        for query_name in common_queries:
            baseline_times = baseline_data[query_name]
            scaled_times = scaled_data[query_name]
            
            baseline_mean = sum(baseline_times) / len(baseline_times)
            scaled_mean = sum(scaled_times) / len(scaled_times)
            
            speedup = baseline_mean / scaled_mean if scaled_mean > 0 else 0
            speedups.append(speedup)
            
            # Calculate efficiency if we know the number of workers
            if scaled_workers:
                ideal_speedup = scaled_workers / baseline_workers
                efficiency = (speedup / ideal_speedup * 100) if ideal_speedup > 0 else 0
                efficiencies.append(efficiency)
            else:
                efficiency = None
            
            result["query_speedups"][query_name] = {
                "baseline_mean_time": baseline_mean,
                "scaled_mean_time": scaled_mean,
                "speedup": speedup,
                "efficiency_percent": efficiency,
                "is_faster": speedup > 1.0,
            }
        
        # Overall statistics
        if speedups:
            result["overall"] = {
                "average_speedup": sum(speedups) / len(speedups),
                "median_speedup": sorted(speedups)[len(speedups) // 2],
                "min_speedup": min(speedups),
                "max_speedup": max(speedups),
            }
            
            if scaled_workers and efficiencies:
                result["overall"]["average_efficiency_percent"] = sum(efficiencies) / len(efficiencies)
                result["overall"]["ideal_speedup"] = scaled_workers / baseline_workers
        
        return result
    
    def calculate_scaleup(
        self,
        small_dataset_experiment_id: int,
        large_dataset_experiment_id: int,
        small_dataset_size: float,
        large_dataset_size: float,
        workers_small: int = 1,
        workers_large: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate scale-up for handling larger datasets.
        
        Scale-up = (T_large / T_small) / (Size_large / Size_small)
        Perfect scale-up = 1.0 (time increases linearly with data size)
        
        Args:
            small_dataset_experiment_id: Experiment with smaller dataset
            large_dataset_experiment_id: Experiment with larger dataset
            small_dataset_size: Size of small dataset (e.g., scale factor)
            large_dataset_size: Size of large dataset
            workers_small: Workers used for small dataset
            workers_large: Workers used for large dataset
            
        Returns:
            Scale-up analysis results
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for scale-up analysis")
        
        # Get data
        small_data = self._get_experiment_execution_times(small_dataset_experiment_id)
        large_data = self._get_experiment_execution_times(large_dataset_experiment_id)
        
        if not small_data or not large_data:
            return {"error": "Could not retrieve experiment data"}
        
        result = {
            "small_dataset_experiment_id": small_dataset_experiment_id,
            "large_dataset_experiment_id": large_dataset_experiment_id,
            "small_dataset_size": small_dataset_size,
            "large_dataset_size": large_dataset_size,
            "size_ratio": large_dataset_size / small_dataset_size if small_dataset_size > 0 else 0,
            "workers_small": workers_small,
            "workers_large": workers_large,
            "query_scaleups": {}
        }
        
        # Find common queries
        common_queries = set(small_data.keys()) & set(large_data.keys())
        
        if not common_queries:
            return {**result, "error": "No common queries found"}
        
        size_ratio = large_dataset_size / small_dataset_size if small_dataset_size > 0 else 0
        scaleups = []
        
        for query_name in common_queries:
            small_times = small_data[query_name]
            large_times = large_data[query_name]
            
            small_mean = sum(small_times) / len(small_times)
            large_mean = sum(large_times) / len(large_times)
            
            time_ratio = large_mean / small_mean if small_mean > 0 else 0
            scaleup = time_ratio / size_ratio if size_ratio > 0 else 0
            scaleups.append(scaleup)
            
            # Scale-up < 1.0 means sublinear scaling (good)
            # Scale-up = 1.0 means linear scaling
            # Scale-up > 1.0 means superlinear scaling (bad)
            
            result["query_scaleups"][query_name] = {
                "small_mean_time": small_mean,
                "large_mean_time": large_mean,
                "time_ratio": time_ratio,
                "scaleup": scaleup,
                "scaling_type": "sublinear" if scaleup < 1.0 else ("linear" if abs(scaleup - 1.0) < 0.1 else "superlinear"),
            }
        
        # Overall statistics
        if scaleups:
            avg_scaleup = sum(scaleups) / len(scaleups)
            result["overall"] = {
                "average_scaleup": avg_scaleup,
                "median_scaleup": sorted(scaleups)[len(scaleups) // 2],
                "min_scaleup": min(scaleups),
                "max_scaleup": max(scaleups),
                "overall_scaling_type": "sublinear" if avg_scaleup < 1.0 else ("linear" if abs(avg_scaleup - 1.0) < 0.1 else "superlinear"),
            }
        
        return result
    
    def analyze_worker_scaling(
        self,
        experiment_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze how performance scales with different worker counts.
        
        Args:
            experiment_configs: List of dicts with 'experiment_id' and 'worker_count'
            
        Returns:
            Worker scaling analysis
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for worker scaling analysis")
        
        if len(experiment_configs) < 2:
            return {"error": "Need at least 2 experiments with different worker counts"}
        
        # Sort by worker count
        configs = sorted(experiment_configs, key=lambda x: x['worker_count'])
        
        result = {
            "configurations": configs,
            "query_scaling": {}
        }
        
        # Collect data for all experiments
        all_data = {}
        for config in configs:
            exp_id = config['experiment_id']
            all_data[exp_id] = {
                "worker_count": config['worker_count'],
                "execution_times": self._get_experiment_execution_times(exp_id)
            }
        
        # Find common queries across all experiments
        query_sets = [set(data['execution_times'].keys()) for data in all_data.values()]
        common_queries = set.intersection(*query_sets) if query_sets else set()
        
        # Analyze scaling for each query
        for query_name in common_queries:
            scaling_data = []
            
            for config in configs:
                exp_id = config['experiment_id']
                worker_count = config['worker_count']
                times = all_data[exp_id]['execution_times'][query_name]
                mean_time = sum(times) / len(times)
                
                scaling_data.append({
                    "worker_count": worker_count,
                    "mean_time": mean_time,
                })
            
            # Calculate efficiency relative to baseline (first config)
            baseline_time = scaling_data[0]['mean_time']
            baseline_workers = scaling_data[0]['worker_count']
            
            for data in scaling_data:
                ideal_speedup = data['worker_count'] / baseline_workers if baseline_workers > 0 else 1
                actual_speedup = baseline_time / data['mean_time'] if data['mean_time'] > 0 else 0
                efficiency = (actual_speedup / ideal_speedup * 100) if ideal_speedup > 0 else 0
                
                data['ideal_speedup'] = ideal_speedup
                data['actual_speedup'] = actual_speedup
                data['efficiency_percent'] = efficiency
            
            result["query_scaling"][query_name] = scaling_data
        
        return result
    
    def _get_experiment_execution_times(self, experiment_id: int) -> Dict[str, List[float]]:
        """
        Get execution times grouped by query for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Dictionary mapping query names to lists of execution times
        """
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
