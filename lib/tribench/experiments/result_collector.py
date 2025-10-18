"""Result collection and storage for experiments."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.result import Result

logger = logging.getLogger(__name__)


class ResultCollector:
    """
    Collects and stores experiment results in structured format.
    
    Handles:
    - Execution time measurement
    - Query statistics aggregation
    - Result validation
    - JSON storage
    """
    
    def __init__(self, results_dir: Optional[Path] = None):
        """
        Initialize the ResultCollector.
        
        Args:
            results_dir: Directory to store results. If None, use default.
        """
        if results_dir is None:
            # Default to tribench-framework/results/
            root_path = Path(__file__).parent.parent.parent.parent
            results_dir = root_path / "results"
        
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"ResultCollector initialized with dir: {self.results_dir}")
    
    def create_result(self,
                     experiment_name: str,
                     experiment_type: str,
                     duration_seconds: float,
                     status: str,
                     query_metadata: Optional[Dict[str, Any]] = None,
                     validation_results: Optional[Dict[str, Any]] = None,
                     error: Optional[Exception] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Result:
        """
        Create a Result object from experiment execution data.
        
        Args:
            experiment_name: Name of the experiment
            experiment_type: Type of experiment (e.g., "trino_query")
            duration_seconds: Total experiment duration
            status: Execution status ("success", "failed", "timeout")
            query_metadata: Query execution statistics from QueryExecutor
            validation_results: Validation results dictionary
            error: Exception if execution failed
            metadata: Additional metadata
            
        Returns:
            Result object
        """
        result = Result(
            experiment_name=experiment_name,
            experiment_type=experiment_type,
            timestamp=datetime.now(),
            duration_seconds=duration_seconds,
            status=status,
        )
        
        # Add query metrics if available
        if query_metadata:
            result.execution_time = query_metadata.get("execution_time_seconds")
            result.rows_returned = query_metadata.get("rows_returned")
            result.data_scanned = query_metadata.get("processed_bytes")
            
            # Add Trino-specific metrics to system_metrics
            trino_metrics = {
                "query_id": query_metadata.get("query_id"),
                "state": query_metadata.get("state"),
                "cpu_time_ms": query_metadata.get("cpu_time_ms"),
                "queued_time_ms": query_metadata.get("queued_time_ms"),
                "elapsed_time_ms": query_metadata.get("elapsed_time_ms"),
                "scheduled_time_ms": query_metadata.get("scheduled_time_ms"),
                "processed_rows": query_metadata.get("processed_rows"),
                "processed_bytes": query_metadata.get("processed_bytes"),
                "peak_memory_bytes": query_metadata.get("peak_memory_bytes"),
                "retry_attempts": query_metadata.get("retry_attempts", 0),
            }
            result.system_metrics.update(trino_metrics)
        
        # Add validation results
        if validation_results:
            result.validation_passed = validation_results.get("passed", True)
            result.validation_errors = validation_results.get("errors", [])
        
        # Add error information
        if error:
            result.error_message = str(error)
            import traceback
            result.error_traceback = traceback.format_exc()
        
        # Add additional metadata
        if metadata:
            result.metadata.update(metadata)
        
        logger.debug(f"Created result for {experiment_name}: {status}")
        return result
    
    def save_result(self, 
                   result: Result,
                   filename: Optional[str] = None) -> Path:
        """
        Save result to JSON file.
        
        Args:
            result: Result object to save
            filename: Custom filename (optional, auto-generated if None)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            # Generate filename: experiment-name_timestamp.json
            timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{result.experiment_name}_{timestamp_str}.json"
        
        # Sanitize filename
        filename = filename.replace(" ", "_").replace("/", "-")
        if not filename.endswith(".json"):
            filename += ".json"
        
        filepath = self.results_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            
            logger.info(f"Saved result to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
            raise
    
    def load_result(self, filepath: Path) -> Result:
        """
        Load result from JSON file.
        
        Args:
            filepath: Path to JSON result file
            
        Returns:
            Result object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Result file not found: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            result = Result.from_dict(data)
            logger.debug(f"Loaded result from: {filepath}")
            return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load result: {e}") from e
    
    def list_results(self, 
                    experiment_name: Optional[str] = None,
                    limit: Optional[int] = None) -> List[Path]:
        """
        List result files in results directory.
        
        Args:
            experiment_name: Filter by experiment name (optional)
            limit: Maximum number of results to return
            
        Returns:
            List of result file paths, sorted by modification time (newest first)
        """
        # Find all JSON files
        result_files = list(self.results_dir.glob("*.json"))
        
        # Filter by experiment name if specified
        if experiment_name:
            result_files = [
                f for f in result_files 
                if f.stem.startswith(experiment_name)
            ]
        
        # Sort by modification time (newest first)
        result_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Apply limit
        if limit:
            result_files = result_files[:limit]
        
        return result_files
    
    def aggregate_results(self, 
                         results: List[Result]) -> Dict[str, Any]:
        """
        Aggregate statistics from multiple results.
        
        Args:
            results: List of Result objects
            
        Returns:
            Dictionary with aggregated statistics
        """
        if not results:
            return {}
        
        execution_times = [
            r.execution_time for r in results 
            if r.execution_time is not None
        ]
        
        rows_returned = [
            r.rows_returned for r in results 
            if r.rows_returned is not None
        ]
        
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        
        aggregated = {
            "total_runs": len(results),
            "successful_runs": success_count,
            "failed_runs": failed_count,
            "success_rate": success_count / len(results) if results else 0,
        }
        
        if execution_times:
            import statistics
            aggregated["execution_time"] = {
                "mean": statistics.mean(execution_times),
                "median": statistics.median(execution_times),
                "stdev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                "min": min(execution_times),
                "max": max(execution_times),
            }
        
        if rows_returned:
            aggregated["rows_returned"] = {
                "mean": sum(rows_returned) / len(rows_returned),
                "min": min(rows_returned),
                "max": max(rows_returned),
            }
        
        return aggregated
    
    def generate_summary(self, results: List[Result]) -> str:
        """
        Generate human-readable summary of results.
        
        Args:
            results: List of Result objects
            
        Returns:
            Summary string
        """
        if not results:
            return "No results available"
        
        stats = self.aggregate_results(results)
        
        lines = [
            f"Experiment Summary: {results[0].experiment_name}",
            f"Total Runs: {stats['total_runs']}",
            f"Success Rate: {stats['success_rate']:.1%}",
        ]
        
        if "execution_time" in stats:
            exec_time = stats["execution_time"]
            lines.extend([
                f"",
                f"Execution Time:",
                f"  Mean: {exec_time['mean']:.3f}s",
                f"  Median: {exec_time['median']:.3f}s",
                f"  StdDev: {exec_time['stdev']:.3f}s",
                f"  Range: {exec_time['min']:.3f}s - {exec_time['max']:.3f}s",
            ])
        
        if "rows_returned" in stats:
            rows = stats["rows_returned"]
            lines.extend([
                f"",
                f"Rows Returned: {rows['mean']:.0f} (avg)",
            ])
        
        return "\n".join(lines)

