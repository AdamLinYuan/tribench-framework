"""Performance analysis for benchmark results."""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime
from .statistical import StatisticalAnalyzer

if TYPE_CHECKING:
    from tribench.storage.result_storage import ResultStorage

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Performance analysis for query executions.
    
    Provides metrics for:
    - Query execution time analysis
    - Throughput metrics (queries/sec, rows/sec, MB/sec)
    - Performance comparison between runs
    """
    
    def __init__(self, storage: 'ResultStorage'):
        """
        Initialize performance analyzer.
        
        Args:
            result_storage: Optional ResultStorage instance for database queries
        """
        self.result_storage = storage
        self.statistical = StatisticalAnalyzer()
    
    def analyze_query_performance(
        self,
        query_name: str,
        experiment_id: Optional[int] = None,
        run_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Analyze performance of a specific query across runs.
        
        Args:
            query_name: Name of the query to analyze
            experiment_id: Optional experiment ID to filter by
            run_ids: Optional list of run IDs to analyze
            
        Returns:
            Dictionary with query performance statistics
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for query performance analysis")
        
        # Fetch query executions from database
        if run_ids:
            executions = []
            for run_id in run_ids:
                run_execs = self.result_storage.get_run_query_executions(run_id)
                executions.extend([e for e in run_execs if e['query_name'] == query_name])
        elif experiment_id:
            # Get all runs for this experiment
            runs = self.result_storage.get_experiment_runs(experiment_id)
            executions = []
            for run in runs:
                run_execs = self.result_storage.get_run_query_executions(run['id'])
                executions.extend([e for e in run_execs if e['query_name'] == query_name])
        else:
            raise ValueError("Either experiment_id or run_ids must be provided")
        
        if not executions:
            return {"error": f"No executions found for query '{query_name}'"}
        
        # Extract metrics
        execution_times = [e['execution_time'] for e in executions if e['status'] == 'completed']
        rows_processed = [e['rows_returned'] for e in executions if e['rows_returned'] is not None]
        bytes_processed = [e['input_bytes'] for e in executions if e['input_bytes'] is not None]
        
        # Calculate statistics
        result = {
            "query_name": query_name,
            "total_executions": len(executions),
            "successful_executions": len(execution_times),
            "failed_executions": len([e for e in executions if e['status'] == 'failed']),
        }
        
        if execution_times:
            result["execution_time"] = self.statistical.calculate_statistics(execution_times)
            result["throughput_qps"] = 1.0 / result["execution_time"]["mean"] if result["execution_time"]["mean"] > 0 else 0
        
        if rows_processed:
            result["rows_processed"] = self.statistical.calculate_statistics(rows_processed)
            if execution_times:
                # Rows per second
                avg_time = result["execution_time"]["mean"]
                avg_rows = result["rows_processed"]["mean"]
                result["rows_per_second"] = avg_rows / avg_time if avg_time > 0 else 0
        
        if bytes_processed:
            result["bytes_processed"] = self.statistical.calculate_statistics(bytes_processed)
            if execution_times:
                # MB per second
                avg_time = result["execution_time"]["mean"]
                avg_bytes = result["bytes_processed"]["mean"]
                result["mb_per_second"] = (avg_bytes / (1024**2)) / avg_time if avg_time > 0 else 0
        
        # Detect outliers in execution time
        if len(execution_times) >= 3:
            outliers = self.statistical.detect_outliers(execution_times, method="iqr")
            if outliers["outliers"]:
                result["outliers"] = outliers
        
        return result
    
    def analyze_experiment_performance(
        self,
        experiment_id: int,
        group_by_query: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze overall experiment performance.
        
        Args:
            experiment_id: Experiment ID to analyze
            group_by_query: If True, provide per-query breakdown
            
        Returns:
            Dictionary with experiment-level performance statistics
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for experiment performance analysis")
        
        # Get experiment info
        experiment = self.result_storage.get_experiment_by_id(experiment_id)
        if not experiment:
            return {"error": f"Experiment {experiment_id} not found"}
        
        # Get all runs
        runs = self.result_storage.get_experiment_runs(experiment_id)
        if not runs:
            return {"error": f"No runs found for experiment {experiment_id}"}
        
        result = {
            "experiment_id": experiment_id,
            "experiment_name": experiment['name'],
            "experiment_type": experiment['experiment_type'],
            "total_runs": len(runs),
            "completed_runs": len([r for r in runs if r['status'] == 'completed']),
            "failed_runs": len([r for r in runs if r['status'] == 'failed']),
        }
        
        # Aggregate all execution times across all runs
        all_execution_times = []
        query_groups = {}
        
        for run in runs:
            executions = self.result_storage.get_run_query_executions(run['id'])
            
            for execution in executions:
                if execution['status'] == 'completed' and execution['execution_time']:
                    all_execution_times.append(execution['execution_time'])
                    
                    # Group by query if requested
                    if group_by_query:
                        query_name = execution['query_name']
                        if query_name not in query_groups:
                            query_groups[query_name] = []
                        query_groups[query_name].append(execution['execution_time'])
        
        # Overall statistics
        if all_execution_times:
            result["overall_execution_time"] = self.statistical.calculate_statistics(all_execution_times)
            result["total_queries_executed"] = len(all_execution_times)
            result["average_throughput_qps"] = len(all_execution_times) / sum(all_execution_times)
        
        # Per-query statistics
        if group_by_query and query_groups:
            result["per_query_statistics"] = {}
            for query_name, times in query_groups.items():
                result["per_query_statistics"][query_name] = self.statistical.calculate_statistics(times)
        
        # Calculate run durations
        run_durations = []
        for run in runs:
            if run['start_time'] and run['end_time']:
                start = datetime.fromisoformat(run['start_time']) if isinstance(run['start_time'], str) else run['start_time']
                end = datetime.fromisoformat(run['end_time']) if isinstance(run['end_time'], str) else run['end_time']
                duration = (end - start).total_seconds()
                run_durations.append(duration)
        
        if run_durations:
            result["run_duration"] = self.statistical.calculate_statistics(run_durations)
        
        return result
    
    def compare_query_runs(
        self,
        query_name: str,
        run_id_1: int,
        run_id_2: int
    ) -> Dict[str, Any]:
        """
        Compare the same query across two different runs.
        
        Args:
            query_name: Name of the query to compare
            run_id_1: First run ID
            run_id_2: Second run ID
            
        Returns:
            Comparison results
        """
        if not self.result_storage:
            raise ValueError("ResultStorage required for query comparison")
        
        # Get executions for both runs
        exec1 = self.result_storage.get_run_query_executions(run_id_1)
        exec2 = self.result_storage.get_run_query_executions(run_id_2)
        
        # Filter by query name
        exec1_query = [e for e in exec1 if e['query_name'] == query_name and e['status'] == 'completed']
        exec2_query = [e for e in exec2 if e['query_name'] == query_name and e['status'] == 'completed']
        
        if not exec1_query:
            return {"error": f"Query '{query_name}' not found in run {run_id_1}"}
        if not exec2_query:
            return {"error": f"Query '{query_name}' not found in run {run_id_2}"}
        
        time1 = exec1_query[0]['execution_time']
        time2 = exec2_query[0]['execution_time']
        
        difference = time2 - time1
        percent_change = (difference / time1 * 100) if time1 > 0 else 0
        
        return {
            "query_name": query_name,
            "run_1": {
                "run_id": run_id_1,
                "execution_time": time1,
                "rows_returned": exec1_query[0].get('rows_returned'),
                "bytes_processed": exec1_query[0].get('bytes_processed'),
            },
            "run_2": {
                "run_id": run_id_2,
                "execution_time": time2,
                "rows_returned": exec2_query[0].get('rows_returned'),
                "bytes_processed": exec2_query[0].get('bytes_processed'),
            },
            "comparison": {
                "time_difference_seconds": difference,
                "percent_change": percent_change,
                "faster_run": run_id_1 if time1 < time2 else run_id_2,
                "speedup_ratio": time1 / time2 if time2 > 0 else 0,
            }
        }
    
    def calculate_query_complexity(self, execution: Dict[str, Any]) -> str:
        """
        Estimate query complexity based on metrics.
        
        Args:
            execution: Query execution dictionary
            
        Returns:
            Complexity category: "simple", "medium", "complex", "very_complex"
        """
        exec_time = execution.get('execution_time_seconds', 0)
        rows = execution.get('rows_returned', 0)
        bytes_proc = execution.get('bytes_processed', 0)
        
        # Simple heuristic based on execution time and data processed
        if exec_time < 1 and bytes_proc < 1024**2:  # < 1 second, < 1 MB
            return "simple"
        elif exec_time < 10 and bytes_proc < 100 * 1024**2:  # < 10 seconds, < 100 MB
            return "medium"
        elif exec_time < 60 and bytes_proc < 1024**3:  # < 1 minute, < 1 GB
            return "complex"
        else:
            return "very_complex"
