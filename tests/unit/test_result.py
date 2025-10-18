"""Unit tests for Result data class."""

import pytest
from datetime import datetime
from tribench.core.result import Result


@pytest.mark.unit
class TestResult:
    """Tests for Result data class."""

    def test_result_creation(self):
        """Test creating a result object."""
        result = Result(
            experiment_name="test-exp",
            experiment_type="sql",
            timestamp=datetime.now(),
            duration_seconds=1.5,
            status="success",
            execution_time=1.2,
            rows_returned=100,
        )

        assert result.experiment_name == "test-exp"
        assert result.experiment_type == "sql"
        assert result.status == "success"
        assert result.execution_time == 1.2
        assert result.rows_returned == 100

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        timestamp = datetime.now()
        result = Result(
            experiment_name="test-exp",
            experiment_type="sql",
            timestamp=timestamp,
            duration_seconds=1.5,
            status="success",
        )

        result_dict = result.to_dict()

        assert result_dict["experiment_name"] == "test-exp"
        assert result_dict["status"] == "success"
        assert result_dict["duration_seconds"] == 1.5
        assert "timestamp" in result_dict

    def test_result_from_dict(self):
        """Test creating result from dictionary."""
        timestamp = datetime.now()
        data = {
            "experiment_name": "test-exp",
            "experiment_type": "sql",
            "timestamp": timestamp.isoformat(),
            "duration_seconds": 1.5,
            "status": "success",
            "execution_time": None,
            "cpu_time": None,
            "memory_usage": None,
            "data_scanned": None,
            "rows_returned": None,
            "system_metrics": {},
            "validation_passed": True,
            "validation_errors": [],
            "metadata": {},
            "error_message": None,
            "error_traceback": None,
        }

        result = Result.from_dict(data)

        assert result.experiment_name == "test-exp"
        assert result.status == "success"
        assert isinstance(result.timestamp, datetime)
