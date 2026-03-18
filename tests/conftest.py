import pytest
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tribench.storage.models import Base
from tribench.storage import connection as db_connection


# ---------------------------------------------------------------------------
# Bundle fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_bundle_dir():
    """Creates a temporary valid TriBench bundle directory structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for d in ("config", "config/hosts", "datasets", "experiments",
                  "queries", "systems", "results", "log"):
            (temp_path / d).mkdir(parents=True, exist_ok=True)

        manifest_data = {"name": "test-bundle", "version": "1.0.0"}
        with open(temp_path / "bundle.yaml", "w") as f:
            yaml.dump(manifest_data, f)

        yield temp_path


# ---------------------------------------------------------------------------
# Database fixtures  (in-memory SQLite, isolated per test)
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(in_memory_engine):
    """Provide a transactional SQLAlchemy session that rolls back after each test."""
    SessionFactory = sessionmaker(bind=in_memory_engine)
    session = SessionFactory()
    yield session
    session.close()


@pytest.fixture(autouse=False)
def isolated_db(tmp_path):
    """
    Point the global ResultStorage helpers at a fresh in-memory database.
    Resets global state after the test.
    """
    db_connection.set_db_url("sqlite:///:memory:")
    db_connection.init_database()
    yield
    db_connection.close_database()
    db_connection.clear_db_url()


# ---------------------------------------------------------------------------
# CLI fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cli_runner():
    """Click test runner with mix_stderr disabled for clean output."""
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# ExperimentConfig YAML fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_experiment_yaml(tmp_path):
    """Write a minimal valid experiment YAML and return its Path."""
    data = {
        "name": "test-experiment",
        "description": "Unit test experiment",
        "system": "trino",
        "runs": 3,
        "warmup_runs": 1,
        "timeout_seconds": 60,
        "connection": {"host": "localhost", "port": 8080},
        "metadata": {"benchmark": "TPC-H", "scale_factor": 1},
    }
    yaml_path = tmp_path / "test_experiment.yaml"
    yaml_path.write_text(yaml.dump(data))
    return yaml_path


@pytest.fixture
def sample_result():
    """Return a pre-built Result instance."""
    from tribench.core.result import Result
    return Result(
        experiment_name="test-exp",
        experiment_type="trino",
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
        duration_seconds=5.0,
        status="success",
        execution_time=4.8,
        rows_returned=1000,
    )
