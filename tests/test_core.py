"""Tests for core dataclasses: ExperimentConfig and Result."""

import pytest
import yaml
from datetime import datetime
from pathlib import Path

from tribench.core.experiment import ExperimentConfig
from tribench.core.result import Result
from tribench.defaults import Defaults


# ---------------------------------------------------------------------------
# ExperimentConfig — construction and defaults
# ---------------------------------------------------------------------------

class TestExperimentConfigDefaults:
    def test_minimal_construction(self):
        cfg = ExperimentConfig(name="x", description="", system="trino")
        assert cfg.name == "x"
        assert cfg.system == "trino"
        assert cfg.runs == 1
        assert cfg.warmup_runs == 0
        assert cfg.parallel_queries == 1
        assert cfg.timeout_seconds == Defaults.Timeouts.QUERY
        assert cfg.max_retries == Defaults.Retry.DEFAULT_MAX_RETRIES
        assert cfg.queries == []
        assert cfg.query_files == []
        assert cfg.connection == {}
        assert cfg.validation == {}
        assert cfg.metadata == {}
        assert "execution_time" in cfg.metrics

    def test_to_dict_contains_all_keys(self):
        cfg = ExperimentConfig(name="d", description="desc", system="trino")
        d = cfg.to_dict()
        for key in ("name", "description", "system", "runs", "warmup_runs",
                    "timeout_seconds", "max_retries", "parallel_queries",
                    "queries", "query_files", "connection", "validation",
                    "metrics", "metadata"):
            assert key in d

    def test_to_dict_values_match(self):
        cfg = ExperimentConfig(name="v", description="", system="trino", runs=5)
        assert cfg.to_dict()["runs"] == 5


# ---------------------------------------------------------------------------
# ExperimentConfig.from_yaml
# ---------------------------------------------------------------------------

class TestExperimentConfigFromYaml:
    def test_loads_minimal_yaml(self, sample_experiment_yaml):
        cfg = ExperimentConfig.from_yaml(sample_experiment_yaml)
        assert cfg.name == "test-experiment"
        assert cfg.system == "trino"
        assert cfg.runs == 3
        assert cfg.warmup_runs == 1

    def test_loads_connection_dict(self, sample_experiment_yaml):
        cfg = ExperimentConfig.from_yaml(sample_experiment_yaml)
        assert cfg.connection["host"] == "localhost"
        assert cfg.connection["port"] == 8080

    def test_loads_metadata(self, sample_experiment_yaml):
        cfg = ExperimentConfig.from_yaml(sample_experiment_yaml)
        assert cfg.metadata["benchmark"] == "TPC-H"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ExperimentConfig.from_yaml(tmp_path / "nonexistent.yaml")

    def test_empty_yaml_raises(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("")
        with pytest.raises(ValueError, match="Empty YAML"):
            ExperimentConfig.from_yaml(p)

    def test_missing_required_fields_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({"name": "only-name"}))
        with pytest.raises(ValueError, match="Missing required fields"):
            ExperimentConfig.from_yaml(p)

    def test_invalid_yaml_syntax_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("name: test\n  broken: :\n  indent")
        with pytest.raises(ValueError):
            ExperimentConfig.from_yaml(p)

    def test_query_files_normalised_to_list(self, tmp_path):
        """A scalar query_files value should become a single-element list."""
        data = {"name": "qf", "system": "trino", "query_files": "queries/q01.sql"}
        p = tmp_path / "qf.yaml"
        p.write_text(yaml.dump(data))
        cfg = ExperimentConfig.from_yaml(p)
        assert isinstance(cfg.query_files, list)
        assert cfg.query_files == ["queries/q01.sql"]

    def test_raw_config_stored(self, sample_experiment_yaml):
        cfg = ExperimentConfig.from_yaml(sample_experiment_yaml)
        assert cfg.raw_config["name"] == "test-experiment"


# ---------------------------------------------------------------------------
# ExperimentConfig — CLI overrides
# ---------------------------------------------------------------------------

class TestExperimentConfigCliOverrides:
    def test_cli_override_scalar(self, sample_experiment_yaml):
        cfg = ExperimentConfig.from_yaml(sample_experiment_yaml, cli_overrides={"runs": 10})
        assert cfg.runs == 10

    def test_cli_override_nested_dict(self, sample_experiment_yaml):
        cfg = ExperimentConfig.from_yaml(
            sample_experiment_yaml,
            cli_overrides={"connection": {"host": "remote-host", "port": 9090}},
        )
        assert cfg.connection["host"] == "remote-host"
        assert cfg.connection["port"] == 9090

    def test_cli_override_does_not_affect_other_fields(self, sample_experiment_yaml):
        cfg = ExperimentConfig.from_yaml(sample_experiment_yaml, cli_overrides={"runs": 99})
        assert cfg.warmup_runs == 1  # unchanged from YAML


# ---------------------------------------------------------------------------
# ExperimentConfig — suite defaults
# ---------------------------------------------------------------------------

class TestExperimentConfigSuiteDefaults:
    def test_suite_default_applied_when_missing_in_yaml(self, tmp_path):
        data = {"name": "e", "system": "trino"}
        p = tmp_path / "e.yaml"
        p.write_text(yaml.dump(data))
        cfg = ExperimentConfig.from_yaml(p, suite_config={"runs": 7})
        assert cfg.runs == 7

    def test_yaml_overrides_suite_default(self, sample_experiment_yaml):
        # The sample YAML sets runs=3; suite default of 99 should be ignored
        cfg = ExperimentConfig.from_yaml(sample_experiment_yaml, suite_config={"runs": 99})
        assert cfg.runs == 3

    def test_suite_connection_merged(self, tmp_path):
        data = {"name": "e", "system": "trino"}
        p = tmp_path / "e.yaml"
        p.write_text(yaml.dump(data))
        cfg = ExperimentConfig.from_yaml(
            p, suite_config={"connection": {"host": "suite-host", "port": 1234}}
        )
        assert cfg.connection["host"] == "suite-host"


# ---------------------------------------------------------------------------
# ExperimentConfig._deep_merge
# ---------------------------------------------------------------------------

class TestDeepMerge:
    def test_scalar_override(self):
        base = {"a": 1, "b": 2}
        ExperimentConfig._deep_merge(base, {"b": 99})
        assert base == {"a": 1, "b": 99}

    def test_nested_dict_merge(self):
        base = {"conn": {"host": "old", "port": 8080}}
        ExperimentConfig._deep_merge(base, {"conn": {"host": "new"}})
        assert base["conn"]["host"] == "new"
        assert base["conn"]["port"] == 8080  # unchanged

    def test_adds_new_key(self):
        base = {"a": 1}
        ExperimentConfig._deep_merge(base, {"b": 2})
        assert base["b"] == 2


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

class TestResult:
    def test_construction_required_fields(self):
        r = Result(
            experiment_name="exp",
            experiment_type="trino",
            timestamp=datetime(2025, 6, 1),
            duration_seconds=3.14,
            status="success",
        )
        assert r.experiment_name == "exp"
        assert r.status == "success"
        assert r.validation_passed is True
        assert r.validation_errors == []

    def test_to_dict_keys(self, sample_result):
        d = sample_result.to_dict()
        for key in ("experiment_name", "experiment_type", "timestamp",
                    "duration_seconds", "status", "execution_time",
                    "rows_returned", "validation_passed", "validation_errors"):
            assert key in d

    def test_to_dict_timestamp_is_isoformat(self, sample_result):
        d = sample_result.to_dict()
        assert d["timestamp"] == "2025-01-01T12:00:00"

    def test_from_dict_roundtrip(self, sample_result):
        d = sample_result.to_dict()
        r2 = Result.from_dict(d)
        assert r2.experiment_name == sample_result.experiment_name
        assert r2.duration_seconds == sample_result.duration_seconds
        assert r2.timestamp == sample_result.timestamp

    def test_optional_fields_default_none(self):
        r = Result(
            experiment_name="x",
            experiment_type="trino",
            timestamp=datetime.now(),
            duration_seconds=1.0,
            status="success",
        )
        assert r.cpu_time is None
        assert r.memory_usage is None
        assert r.data_scanned is None
        assert r.error_message is None
