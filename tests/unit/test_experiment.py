"""Unit tests for core Experiment abstraction and experiment engine."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from tribench.core.experiment import Experiment, ExperimentConfig
from tribench.experiments import QueryExecutor, ResultCollector, TrinoExperiment


class MockExperiment(Experiment):
    """Mock implementation of Experiment for testing."""

    def prepare(self):
        """Mock prepare."""
        pass

    def run(self):
        """Mock run."""
        self.start_time = datetime.now()
        self.status = "running"
        # Simulate some work
        self.results = {"query_time": 1.5, "rows": 100}
        self.end_time = datetime.now()
        self.status = "completed"
        return self.results

    def validate(self):
        """Mock validate."""
        expected_rows = self.config.validation.get("expected_rows", 0)
        actual_rows = self.results.get("rows", 0)
        return actual_rows >= expected_rows

    def cleanup(self):
        """Mock cleanup."""
        pass


@pytest.mark.unit
class TestExperiment:
    """Tests for Experiment abstraction."""

    def test_experiment_initialization(self, sample_experiment_config):
        """Test experiment can be initialized with config."""
        exp = MockExperiment(sample_experiment_config)
        assert exp.config.name == "test-experiment"
        assert exp.status == "pending"
        assert exp.start_time is None
        assert exp.end_time is None

    def test_experiment_run(self, sample_experiment_config):
        """Test experiment can be run."""
        exp = MockExperiment(sample_experiment_config)

        results = exp.run()

        assert exp.status == "completed"
        assert exp.start_time is not None
        assert exp.end_time is not None
        assert "query_time" in results
        assert "rows" in results

    def test_experiment_validation(self, sample_experiment_config):
        """Test experiment validation."""
        exp = MockExperiment(sample_experiment_config)
        exp.run()

        # Should pass validation (100 rows >= 10 expected)
        assert exp.validate()

    def test_experiment_duration(self, sample_experiment_config):
        """Test experiment duration calculation."""
        exp = MockExperiment(sample_experiment_config)

        # Duration should be None before running
        assert exp.get_duration() is None

        # Run experiment
        exp.run()

        # Duration should be positive number after running
        duration = exp.get_duration()
        assert duration is not None
        assert duration >= 0


@pytest.mark.unit
class TestExperimentConfig:
    """Tests for ExperimentConfig YAML parsing."""
    
    def test_config_from_yaml_minimal(self, tmp_path):
        """Test loading minimal experiment config from YAML."""
        yaml_content = """
name: "test-exp"
system: "trino"
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        
        config = ExperimentConfig.from_yaml(yaml_file)
        
        assert config.name == "test-exp"
        assert config.system == "trino"
        assert config.runs == 1  # default
        assert config.warmup_runs == 0  # default
    
    def test_config_from_yaml_complete(self, tmp_path):
        """Test loading complete experiment config from YAML."""
        yaml_content = """
name: "complete-exp"
description: "Test experiment"
system: "trino"
runs: 5
warmup_runs: 2
timeout_seconds: 120
queries:
  - "SELECT 1"
  - "SELECT 2"
connection:
  host: "localhost"
  port: 9090
validation:
  min_success_rate: 0.95
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        
        config = ExperimentConfig.from_yaml(yaml_file)
        
        assert config.name == "complete-exp"
        assert config.runs == 5
        assert config.warmup_runs == 2
        assert config.timeout_seconds == 120
        assert len(config.queries) == 2
        assert config.connection["port"] == 9090
        assert config.validation["min_success_rate"] == 0.95
    
    def test_config_missing_file(self):
        """Test error when YAML file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ExperimentConfig.from_yaml(Path("/nonexistent/file.yaml"))
    
    def test_config_missing_required_fields(self, tmp_path):
        """Test error when required fields are missing."""
        yaml_content = """
description: "Missing name and system"
"""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)
        
        with pytest.raises(ValueError, match="Missing required fields"):
            ExperimentConfig.from_yaml(yaml_file)


@pytest.mark.unit
class TestQueryExecutor:
    """Tests for QueryExecutor."""
    
    def test_executor_initialization(self):
        """Test QueryExecutor initialization."""
        executor = QueryExecutor(
            host="testhost",
            port=9090,
            catalog="test_catalog"
        )
        
        assert executor.config.host == "testhost"
        assert executor.config.port == 9090
        assert executor.config.catalog == "test_catalog"
        assert not executor.is_connected()
    
    @patch('tribench.experiments.query_executor.trino.dbapi.connect')
    def test_executor_connect(self, mock_connect):
        """Test connection to Trino."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        executor = QueryExecutor()
        executor.connect()
        
        assert executor.is_connected()
        mock_connect.assert_called_once()
    
    @patch('tribench.experiments.query_executor.trino.dbapi.connect')
    def test_executor_execute_query_success(self, mock_connect):
        """Test successful query execution."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, 'test'), (2, 'data')]
        mock_cursor.stats = {
            'queryId': 'test_query_id',
            'state': 'FINISHED',
            'processedRows': 2,
        }
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        executor = QueryExecutor()
        executor.connect()
        
        rows, metadata = executor.execute_query("SELECT * FROM test")
        
        assert len(rows) == 2
        assert metadata['success'] is True
        assert metadata['rows_returned'] == 2
        assert metadata['query_id'] == 'test_query_id'


@pytest.mark.unit
class TestResultCollector:
    """Tests for ResultCollector."""
    
    def test_collector_initialization(self, tmp_path):
        """Test ResultCollector initialization."""
        collector = ResultCollector(tmp_path)
        assert collector.results_dir == tmp_path
        assert tmp_path.exists()
    
    def test_create_result(self, tmp_path):
        """Test creating a Result object."""
        collector = ResultCollector(tmp_path)
        
        query_metadata = {
            'execution_time_seconds': 1.5,
            'rows_returned': 100,
            'query_id': 'test_123',
        }
        
        result = collector.create_result(
            experiment_name="test_exp",
            experiment_type="trino_query",
            duration_seconds=2.0,
            status="success",
            query_metadata=query_metadata
        )
        
        assert result.experiment_name == "test_exp"
        assert result.status == "success"
        assert result.execution_time == 1.5
        assert result.rows_returned == 100
    
    def test_save_and_load_result(self, tmp_path):
        """Test saving and loading results."""
        collector = ResultCollector(tmp_path)
        
        result = collector.create_result(
            experiment_name="test_exp",
            experiment_type="trino_query",
            duration_seconds=1.0,
            status="success"
        )
        
        # Save result
        filepath = collector.save_result(result)
        assert filepath.exists()
        
        # Load result
        loaded_result = collector.load_result(filepath)
        assert loaded_result.experiment_name == result.experiment_name
        assert loaded_result.status == result.status
    
    def test_aggregate_results(self, tmp_path):
        """Test aggregating multiple results."""
        from tribench.core.result import Result
        
        collector = ResultCollector(tmp_path)
        
        results = [
            Result("test", "query", datetime.now(), 1.0, "success", execution_time=1.0),
            Result("test", "query", datetime.now(), 1.5, "success", execution_time=1.5),
            Result("test", "query", datetime.now(), 1.2, "success", execution_time=1.2),
        ]
        
        stats = collector.aggregate_results(results)
        
        assert stats['total_runs'] == 3
        assert stats['successful_runs'] == 3
        assert stats['success_rate'] == 1.0
        assert 'execution_time' in stats
        assert stats['execution_time']['mean'] == pytest.approx(1.233, 0.01)


