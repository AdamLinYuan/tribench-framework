"""Pytest configuration for TriBench tests."""

import pytest
import sys
from pathlib import Path

# Add lib directory to path so imports work
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))


@pytest.fixture
def sample_system_config():
    """Sample system configuration for testing."""
    return {
        "name": "test-trino",
        "type": "trino",
        "version": "434",
        "coordinator": {"heap_size": "2G", "port": 8080},
    }


@pytest.fixture
def sample_experiment_config():
    """Sample experiment configuration for testing."""
    from tribench.core.experiment import ExperimentConfig

    return ExperimentConfig(
        name="test-experiment",
        description="Test experiment",
        system="trino",
        dataset="test-data",
        queries=["SELECT 1", "SELECT 2"],
        runs=1,
        warmup_runs=0,
        timeout_seconds=60,
        connection={"host": "localhost", "port": 8080},
        validation={"expected_rows": 10, "min_success_rate": 0.9},
        metrics=["execution_time", "rows_returned"],
    )


@pytest.fixture
def sample_dataset_metadata():
    """Sample dataset metadata for testing."""
    from tribench.data.dataset import DatasetMetadata
    from pathlib import Path

    return DatasetMetadata(
        name="test-dataset",
        type="static",
        format="parquet",
        scale_factor=1.0,
        size_bytes=1048576,
        location="/tmp/test-data",
        tables=["test_table"],
        row_counts={"test_table": 1000},
        checksums={"test_table": "abc123"},
        properties={},
        created_at="2025-10-17T00:00:00",
        generator="test"
    )
