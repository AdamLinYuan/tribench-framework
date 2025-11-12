"""
Unit tests for metrics storage system.

Tests TimeSeriesData and MetricsStorage classes.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from tribench.monitoring.storage import TimeSeriesData, MetricsStorage
from tribench.monitoring.base import Metric


class TestTimeSeriesData:
    """Test TimeSeriesData class."""
    
    def test_creation(self):
        """Test creating time series data."""
        data = TimeSeriesData(
            experiment_name="test_exp",
            start_time=datetime.now(),
        )
        
        assert data.experiment_name == "test_exp"
        assert len(data.metrics) == 0
    
    def test_add_metric(self):
        """Test adding metrics."""
        data = TimeSeriesData(
            experiment_name="test",
            start_time=datetime.now(),
        )
        
        metric = Metric(
            timestamp=datetime.now(),
            type="gauge",
            name="test.metric",
            value=100.0,
            unit="bytes",
            labels={},
        )
        
        data.add_metric(metric)
        assert len(data.metrics) == 1
    
    def test_filter_by_name(self):
        """Test filtering metrics by name."""
        data = TimeSeriesData(
            experiment_name="test",
            start_time=datetime.now(),
        )
        
        data.add_metrics([
            Metric(datetime.now(), "gauge", "metric.a", 1.0, "count", {}),
            Metric(datetime.now(), "gauge", "metric.b", 2.0, "count", {}),
            Metric(datetime.now(), "gauge", "metric.a", 3.0, "count", {}),
        ])
        
        filtered = data.filter_by_name("metric.a")
        assert len(filtered) == 2
    
    def test_compute_summary(self):
        """Test summary statistics computation."""
        data = TimeSeriesData(
            experiment_name="test",
            start_time=datetime.now(),
        )
        
        # Add metrics with known values
        for value in [10.0, 20.0, 30.0, 40.0, 50.0]:
            data.add_metric(
                Metric(datetime.now(), "gauge", "test.metric", value, "count", {})
            )
        
        summary = data.compute_summary()
        
        assert "test.metric" in summary
        stats = summary["test.metric"]
        
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0
        assert stats["median"] == 30.0
        assert "stddev" in stats


class TestMetricsStorage:
    """Test MetricsStorage class."""
    
    def test_initialization(self):
        """Test storage initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MetricsStorage(storage_dir=tmpdir)
            
            assert storage.storage_dir == Path(tmpdir)
            assert storage.storage_dir.exists()
    
    def test_save_and_load_timeseries(self):
        """Test saving and loading time series data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MetricsStorage(storage_dir=tmpdir)
            
            # Create data
            now = datetime.now()
            data = TimeSeriesData(
                experiment_name="test_exp",
                start_time=now,
                end_time=now,
            )
            
            data.add_metrics([
                Metric(now, "gauge", "test.metric", 100.0, "bytes", {"host": "localhost"}),
                Metric(now, "counter", "test.counter", 5.0, "count", {}),
            ])
            
            data.compute_summary()
            
            # Save
            filepath = storage.save_timeseries(data)
            assert filepath.exists()
            
            # Load
            loaded_data = storage.load_timeseries(filepath)
            
            assert loaded_data.experiment_name == "test_exp"
            assert len(loaded_data.metrics) == 2
            assert loaded_data.summary is not None
    
    def test_export_to_csv(self):
        """Test CSV export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MetricsStorage(storage_dir=tmpdir)
            
            # Create data
            now = datetime.now()
            data = TimeSeriesData(
                experiment_name="test",
                start_time=now,
            )
            
            data.add_metric(
                Metric(now, "gauge", "test.metric", 100.0, "bytes", {"host": "localhost"})
            )
            
            # Export
            csv_path = Path(tmpdir) / "test.csv"
            storage.export_to_csv(data, csv_path)
            
            assert csv_path.exists()
            
            # Verify CSV content
            content = csv_path.read_text()
            assert "timestamp" in content
            assert "test.metric" in content
            assert "100.0" in content
    
    def test_buffer_operations(self):
        """Test buffered metric operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MetricsStorage(
                storage_dir=tmpdir,
                auto_flush=False,
                buffer_size=10,
            )
            
            # Add metrics to buffer
            for i in range(5):
                metric = Metric(
                    datetime.now(),
                    "gauge",
                    "test.metric",
                    float(i),
                    "count",
                    {},
                )
                storage.append_metric(metric)
            
            assert storage.get_buffer_size() == 5
            
            # Flush buffer
            filepath = storage.flush_buffer()
            assert filepath is not None
            assert filepath.exists()
            assert storage.get_buffer_size() == 0
    
    def test_list_files(self):
        """Test listing storage files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MetricsStorage(storage_dir=tmpdir)
            
            # Create some files
            data = TimeSeriesData("test", datetime.now())
            data.add_metric(Metric(datetime.now(), "gauge", "test", 1.0, "count", {}))
            
            storage.save_timeseries(data, "file1.json")
            storage.save_timeseries(data, "file2.json")
            
            files = storage.list_files()
            assert len(files) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
