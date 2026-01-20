"""
Metrics storage implementation.

Provides persistent storage for monitoring metrics with support for:
- Time-series data storage in JSON format
- CSV export for external analysis
- Data aggregation and summarization
- Query and filtering capabilities
"""

import json
import csv
import gzip
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict

from .base import Metric

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesData:
    """
    Container for time-series metrics data.
    
    Stores a collection of metrics with associated metadata for
    persistence and analysis.
    """
    
    # Metadata
    experiment_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Metrics
    metrics: List[Metric] = None
    
    # Summary statistics
    summary: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize empty collections."""
        if self.metrics is None:
            self.metrics = []
        if self.summary is None:
            self.summary = {}
    
    def add_metric(self, metric: Metric) -> None:
        """Add a metric to the time series."""
        self.metrics.append(metric)
    
    def add_metrics(self, metrics: List[Metric]) -> None:
        """Add multiple metrics to the time series."""
        self.metrics.extend(metrics)
    
    def filter_by_name(self, name: str) -> List[Metric]:
        """Filter metrics by name."""
        return [m for m in self.metrics if m.name == name]
    
    def filter_by_type(self, metric_type: str) -> List[Metric]:
        """Filter metrics by type."""
        return [m for m in self.metrics if m.type == metric_type]
    
    def filter_by_label(self, key: str, value: str) -> List[Metric]:
        """Filter metrics by label key-value pair."""
        return [m for m in self.metrics if m.labels.get(key) == value]
    
    def get_metric_names(self) -> List[str]:
        """Get unique metric names."""
        return list(set(m.name for m in self.metrics))
    
    def compute_summary(self) -> Dict[str, Any]:
        """
        Compute summary statistics for the time series.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.metrics:
            return {}
        
        # Group metrics by name
        by_name = defaultdict(list)
        for metric in self.metrics:
            by_name[metric.name].append(metric.value)
        
        # Compute statistics for each metric
        summary = {}
        for name, values in by_name.items():
            if not values:
                continue
            
            summary[name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
            }
            
            # Compute median
            sorted_values = sorted(values)
            n = len(sorted_values)
            if n % 2 == 0:
                summary[name]["median"] = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                summary[name]["median"] = sorted_values[n//2]
            
            # Compute standard deviation if more than 1 value
            if len(values) > 1:
                mean = summary[name]["mean"]
                variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                summary[name]["stddev"] = variance ** 0.5
        
        self.summary = summary
        return summary


class MetricsStorage:
    """
    Persistent storage for monitoring metrics.
    
    Provides:
    - JSON storage with optional compression
    - CSV export for external analysis
    - Data loading and querying
    - Automatic directory management
    """
    
    def __init__(self, 
                 storage_dir: Union[str, Path],
                 compress: bool = False,
                 auto_flush: bool = True,
                 buffer_size: int = 1000):
        """
        Initialize metrics storage.
        
        Args:
            storage_dir: Directory for storing metrics files
            compress: Use gzip compression for JSON files
            auto_flush: Automatically flush buffer when full
            buffer_size: Number of metrics to buffer before flushing
        """
        self.storage_dir = Path(storage_dir)
        self.compress = compress
        self.auto_flush = auto_flush
        self.buffer_size = buffer_size
        
        # Create directory if needed
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Buffer for metrics
        self._buffer: List[Metric] = []
        self._current_file: Optional[Path] = None
        
        logger.info(f"Initialized metrics storage at {self.storage_dir}")
    
    def save_timeseries(self, 
                       data: TimeSeriesData,
                       filename: Optional[str] = None) -> Path:
        """
        Save time series data to JSON file.
        
        Args:
            data: TimeSeriesData to save
            filename: Custom filename (auto-generated if None)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            # Generate filename from metadata
            timestamp = data.start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"{data.experiment_name}_{timestamp}.json"
        
        if self.compress and not filename.endswith('.gz'):
            filename += '.gz'
        
        filepath = self.storage_dir / filename
        
        # Convert to serializable format
        data_dict = {
            "experiment_name": data.experiment_name,
            "start_time": data.start_time.isoformat(),
            "end_time": data.end_time.isoformat() if data.end_time else None,
            "metrics": [self._metric_to_dict(m) for m in data.metrics],
            "summary": data.summary,
        }
        
        # Write to file
        try:
            if self.compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    json.dump(data_dict, f, indent=2)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_dict, f, indent=2)
            
            logger.info(f"Saved time series data to {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Failed to save time series data: {e}", exc_info=True)
            raise
    
    def load_timeseries(self, filepath: Union[str, Path]) -> TimeSeriesData:
        """
        Load time series data from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            TimeSeriesData object
        """
        filepath = Path(filepath)
        
        try:
            # Read file (handle compression automatically)
            if filepath.suffix == '.gz':
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    data_dict = json.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data_dict = json.load(f)
            
            # Convert back to TimeSeriesData
            data = TimeSeriesData(
                experiment_name=data_dict["experiment_name"],
                start_time=datetime.fromisoformat(data_dict["start_time"]),
                end_time=datetime.fromisoformat(data_dict["end_time"]) if data_dict.get("end_time") else None,
                metrics=[self._dict_to_metric(m) for m in data_dict.get("metrics", [])],
                summary=data_dict.get("summary", {}),
            )
            
            logger.debug(f"Loaded time series data from {filepath}")
            return data
        
        except Exception as e:
            logger.error(f"Failed to load time series data from {filepath}: {e}", exc_info=True)
            raise
    
    def export_to_csv(self,
                     data: TimeSeriesData,
                     filepath: Union[str, Path],
                     include_labels: bool = True) -> Path:
        """
        Export time series data to CSV format.
        
        Args:
            data: TimeSeriesData to export
            filepath: Output CSV file path
            include_labels: Include label columns in CSV
            
        Returns:
            Path to exported CSV file
        """
        filepath = Path(filepath)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                # Determine all label keys if including labels
                label_keys = set()
                if include_labels:
                    for metric in data.metrics:
                        label_keys.update(metric.labels.keys())
                label_keys = sorted(label_keys)
                
                # Define CSV columns
                fieldnames = ['timestamp', 'type', 'name', 'value', 'unit']
                if include_labels:
                    fieldnames.extend(label_keys)
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write metrics
                for metric in data.metrics:
                    row = {
                        'timestamp': metric.timestamp.isoformat(),
                        'type': metric.metric_type.value,  # Use metric_type, not type
                        'name': metric.name,
                        'value': metric.value,
                        'unit': metric.unit,
                    }
                    
                    # Add label values
                    if include_labels:
                        for key in label_keys:
                            row[key] = metric.labels.get(key, '')
                    
                    writer.writerow(row)
            
            logger.info(f"Exported time series data to CSV: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}", exc_info=True)
            raise
    
    def list_files(self, pattern: str = "*.json*") -> List[Path]:
        """
        List metrics files in storage directory.
        
        Args:
            pattern: Glob pattern for filtering files
            
        Returns:
            List of file paths
        """
        return sorted(self.storage_dir.glob(pattern))
    
    def append_metric(self, metric: Metric) -> None:
        """
        Append a metric to the buffer.
        
        Automatically flushes if buffer is full and auto_flush is enabled.
        
        Args:
            metric: Metric to append
        """
        self._buffer.append(metric)
        
        if self.auto_flush and len(self._buffer) >= self.buffer_size:
            self.flush_buffer()
    
    def append_metrics(self, metrics: List[Metric]) -> None:
        """
        Append multiple metrics to the buffer.
        
        Args:
            metrics: List of metrics to append
        """
        self._buffer.extend(metrics)
        
        if self.auto_flush and len(self._buffer) >= self.buffer_size:
            self.flush_buffer()
    
    def flush_buffer(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        Flush buffered metrics to file.
        
        Args:
            filename: Custom filename (auto-generated if None)
            
        Returns:
            Path to flushed file or None if buffer was empty
        """
        if not self._buffer:
            return None
        
        # Create TimeSeriesData from buffer
        data = TimeSeriesData(
            experiment_name="buffered_metrics",
            start_time=self._buffer[0].timestamp,
            end_time=self._buffer[-1].timestamp,
            metrics=self._buffer.copy(),
        )
        
        # Compute summary
        data.compute_summary()
        
        # Save to file
        filepath = self.save_timeseries(data, filename)
        
        # Clear buffer
        self._buffer.clear()
        
        logger.info(f"Flushed {len(data.metrics)} metrics to {filepath}")
        return filepath
    
    def clear_buffer(self) -> None:
        """Clear the metrics buffer without saving."""
        self._buffer.clear()
    
    def get_buffer_size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)
    
    # Private helper methods
    
    def _metric_to_dict(self, metric: Metric) -> Dict[str, Any]:
        """Convert Metric to dictionary for serialization."""
        return {
            "timestamp": metric.timestamp.isoformat(),
            "type": metric.metric_type.value,  # Use metric_type, not type
            "name": metric.name,
            "value": metric.value,
            "unit": metric.unit,
            "labels": metric.labels,
        }
    
    def _dict_to_metric(self, data: Dict[str, Any]) -> Metric:
        """Convert dictionary to Metric object."""
        from .base import MetricType
        return Metric(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metric_type=MetricType(data.get("metric_type", data.get("type"))),  # Support both keys for backward compatibility
            name=data["name"],
            value=data["value"],
            unit=data.get("unit", ""),
            labels=data.get("labels", {}),
        )
