"""Test database storage integration with experiments."""

import pytest
from pathlib import Path
from datetime import datetime
from tribench.storage import (
    init_database,
    ResultStorage,
    close_database,
)


@pytest.fixture
def storage(tmp_path):
    """Create a test storage with temporary database."""
    # Use temporary SQLite database
    import os
    os.environ['TRIBENCH_DATABASE_URL'] = f"sqlite:///{tmp_path}/test.db"
    
    # Initialize database
    init_database()
    
    # Create storage instance
    storage = ResultStorage()
    
    yield storage
    
    # Cleanup
    close_database()


def test_create_experiment(storage):
    """Test creating an experiment record."""
    exp_id = storage.create_or_get_experiment(
        name="test_experiment",
        experiment_type="trino_query",
        config={"test": "config"},
        dataset_name="tpch-sf0.01",
        tags=["test", "integration"],
    )
    
    assert exp_id is not None
    assert exp_id > 0
    
    # Verify we can retrieve it (returns dict)
    exp = storage.get_experiment_by_name("test_experiment")
    assert exp is not None
    assert exp["name"] == "test_experiment"
    assert exp["experiment_type"] == "trino_query"
    assert exp["dataset_name"] == "tpch-sf0.01"
    assert "test" in exp["tags"]


def test_create_run(storage):
    """Test creating a run record."""
    # Create experiment
    exp_id = storage.create_or_get_experiment(
        name="test_run_experiment",
        experiment_type="trino_query",
    )
    
    # Create run
    run_id = storage.create_run(
        experiment_id=exp_id,
        run_number=1,
        run_type="measured",
    )
    
    assert run_id is not None
    assert run_id > 0


def test_add_query_execution(storage):
    """Test adding query execution records."""
    # Create experiment and run
    exp_id = storage.create_or_get_experiment(
        name="test_query_experiment",
        experiment_type="trino_query",
    )
    
    run_id = storage.create_run(
        experiment_id=exp_id,
        run_number=1,
        run_type="measured",
    )
    
    # Add query execution
    qe_id = storage.add_query_execution(
        run_id=run_id,
        query_name="q1",
        query_sql="SELECT 1",
        execution_time_ms=123.45,
        status="success",
        trino_query_id="20231115_123456_00001",
        trino_stats={
            "rows_processed": 1000,
            "bytes_processed": 5000,
        },
    )
    
    assert qe_id is not None
    assert qe_id > 0
    
    # Retrieve query executions
    query_execs = storage.get_run_query_executions(run_id)
    assert len(query_execs) == 1
    assert query_execs[0].query_name == "q1"
    assert query_execs[0].execution_time_ms == 123.45


def test_complete_run(storage):
    """Test completing a run."""
    # Create experiment and run
    exp_id = storage.create_or_get_experiment(
        name="test_complete_experiment",
        experiment_type="trino_query",
    )
    
    run_id = storage.create_run(
        experiment_id=exp_id,
        run_number=1,
        run_type="measured",
    )
    
    # Add some query executions
    storage.add_query_execution(
        run_id=run_id,
        query_name="q1",
        query_sql="SELECT 1",
        execution_time_ms=100.0,
        status="success",
    )
    
    storage.add_query_execution(
        run_id=run_id,
        query_name="q2",
        query_sql="SELECT 2",
        execution_time_ms=150.0,
        status="success",
    )
    
    # Complete the run
    storage.complete_run(
        run_id=run_id,
        status="completed",
        total_queries=2,
        queries_succeeded=2,
        queries_failed=0,
        total_execution_time_ms=250.0,
    )
    
    # Verify run is completed
    runs = storage.get_experiment_runs(exp_id)
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].total_queries == 2
    assert runs[0].queries_succeeded == 2


def test_list_experiments(storage):
    """Test listing experiments."""
    # Create multiple experiments
    storage.create_or_get_experiment(
        name="exp1",
        experiment_type="trino_query",
    )
    
    storage.create_or_get_experiment(
        name="exp2",
        experiment_type="trino_query",
    )
    
    storage.create_or_get_experiment(
        name="exp3",
        experiment_type="trino_query",
    )
    
    # List all experiments
    experiments = storage.list_experiments(limit=10)
    assert len(experiments) >= 3
    
    # Check names
    exp_names = [exp.name for exp in experiments]
    assert "exp1" in exp_names
    assert "exp2" in exp_names
    assert "exp3" in exp_names


def test_get_experiment_by_id(storage):
    """Test getting experiment by ID."""
    # Create experiment
    exp_id = storage.create_or_get_experiment(
        name="test_get_by_id",
        experiment_type="trino_query",
        dataset_name="test_dataset",
    )
    
    # Retrieve by ID (returns Experiment object)
    exp = storage.get_experiment_by_id(exp_id)
    assert exp is not None
    assert exp.id == exp_id
    assert exp.name == "test_get_by_id"
    assert exp.dataset_name == "test_dataset"


def test_experiment_runs_relationship(storage):
    """Test relationship between experiments and runs."""
    # Create experiment
    exp_id = storage.create_or_get_experiment(
        name="test_relationship",
        experiment_type="trino_query",
    )
    
    # Create multiple runs
    run1_id = storage.create_run(exp_id, 1, "warmup")
    run2_id = storage.create_run(exp_id, 2, "measured")
    run3_id = storage.create_run(exp_id, 3, "measured")
    
    # Get all runs for experiment
    runs = storage.get_experiment_runs(exp_id)
    assert len(runs) == 3
    assert runs[0].run_number == 1
    assert runs[0].run_type == "warmup"
    assert runs[1].run_number == 2
    assert runs[2].run_number == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
