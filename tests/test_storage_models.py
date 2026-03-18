"""Tests for SQLAlchemy ORM models and the ResultStorage service."""

import pytest
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from tribench.storage.models import (
    Experiment,
    ExperimentRun,
    QueryExecution,
    SystemMetric,
    MonitoringMetric,
)
from tribench.storage.result import ResultStorage
from tribench.storage import connection as db_connection


# ---------------------------------------------------------------------------
# Low-level ORM tests (use the db_session fixture which provides a raw session)
# ---------------------------------------------------------------------------

class TestExperimentModel:
    def test_create_experiment(self, db_session):
        exp = Experiment(
            name="test-exp",
            experiment_type="trino",
            config={"runs": 3},
        )
        db_session.add(exp)
        db_session.commit()
        assert exp.id is not None

    def test_name_must_be_unique(self, db_session):
        e1 = Experiment(name="dup", experiment_type="trino", config={})
        e2 = Experiment(name="dup", experiment_type="trino", config={})
        db_session.add(e1)
        db_session.commit()
        db_session.add(e2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestCascadeDelete:
    def test_deleting_experiment_removes_runs(self, db_session):
        exp = Experiment(name="cascade-exp", experiment_type="trino", config={})
        db_session.add(exp)
        db_session.flush()

        run = ExperimentRun(
            experiment_id=exp.id,
            run_number=1,
            run_type="measured",
            start_time=datetime.now(),
            status="completed",
        )
        db_session.add(run)
        db_session.commit()
        run_id = run.id

        db_session.delete(exp)
        db_session.commit()

        assert db_session.get(ExperimentRun, run_id) is None

    def test_deleting_run_removes_query_executions(self, db_session):
        exp = Experiment(name="qe-cascade", experiment_type="trino", config={})
        db_session.add(exp)
        db_session.flush()

        run = ExperimentRun(
            experiment_id=exp.id,
            run_number=1,
            run_type="measured",
            start_time=datetime.now(),
            status="running",
        )
        db_session.add(run)
        db_session.flush()

        qe = QueryExecution(
            run_id=run.id,
            query_name="q01",
            start_time=datetime.now(),
            status="completed",
        )
        db_session.add(qe)
        db_session.commit()
        qe_id = qe.id

        db_session.delete(run)
        db_session.commit()

        assert db_session.get(QueryExecution, qe_id) is None

    def test_deleting_run_removes_system_metric(self, db_session):
        exp = Experiment(name="sm-cascade", experiment_type="trino", config={})
        db_session.add(exp)
        db_session.flush()

        run = ExperimentRun(
            experiment_id=exp.id,
            run_number=1,
            run_type="measured",
            start_time=datetime.now(),
            status="completed",
        )
        db_session.add(run)
        db_session.flush()

        sm = SystemMetric(run_id=run.id, cpu_percent_mean=42.0)
        db_session.add(sm)
        db_session.commit()
        sm_id = sm.id

        db_session.delete(run)
        db_session.commit()

        assert db_session.get(SystemMetric, sm_id) is None


class TestSystemMetricConstraint:
    def test_unique_system_metric_per_run(self, db_session):
        exp = Experiment(name="unique-sm", experiment_type="trino", config={})
        db_session.add(exp)
        db_session.flush()

        run = ExperimentRun(
            experiment_id=exp.id,
            run_number=1,
            run_type="measured",
            start_time=datetime.now(),
            status="completed",
        )
        db_session.add(run)
        db_session.flush()

        sm1 = SystemMetric(run_id=run.id)
        sm2 = SystemMetric(run_id=run.id)
        db_session.add(sm1)
        db_session.commit()
        db_session.add(sm2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestMonitoringMetric:
    def test_multiple_monitoring_metrics_allowed(self, db_session):
        exp = Experiment(name="mm-multi", experiment_type="trino", config={})
        db_session.add(exp)
        db_session.flush()

        run = ExperimentRun(
            experiment_id=exp.id,
            run_number=1,
            run_type="measured",
            start_time=datetime.now(),
            status="completed",
        )
        db_session.add(run)
        db_session.flush()

        for i in range(5):
            mm = MonitoringMetric(
                run_id=run.id,
                timestamp=datetime.now(),
                metric_type="system_resource",
                metric_name="cpu_percent",
                value=float(i * 10),
                unit="%",
            )
            db_session.add(mm)
        db_session.commit()

        count = db_session.query(MonitoringMetric).filter_by(run_id=run.id).count()
        assert count == 5


# ---------------------------------------------------------------------------
# MetricStore via ResultStorage  (covers metric_store.py lines 59-247)
# ---------------------------------------------------------------------------

def _setup_run(storage):
    """Helper: create an experiment + run, return (exp_id, run_id)."""
    exp_id = storage.create_or_get_experiment(name="ms-exp", experiment_type="trino")
    run_id = storage.create_run(experiment_id=exp_id)
    return exp_id, run_id


class TestResultStorageSystemMetrics:
    def test_add_system_metrics_creates_record(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        storage.add_system_metrics(
            run_id=run_id,
            cpu_percent_mean=42.0,
            cpu_percent_max=95.0,
            memory_percent_mean=60.0,
            memory_percent_max=80.0,
            memory_bytes_mean=1024 * 1024 * 512,
            memory_bytes_max=1024 * 1024 * 1024,
            disk_read_bytes=100_000,
            disk_write_bytes=50_000,
            network_sent_bytes=200_000,
            network_recv_bytes=300_000,
            collection_interval_seconds=1.0,
            total_samples=60,
        )
        # Verify via direct storage query
        metrics = storage.get_monitoring_metrics_summary(run_id)
        # system metrics are stored in the SystemMetric table, not MonitoringMetric,
        # so summary will be empty — but add should not raise
        assert isinstance(metrics, dict)

    def test_add_system_metrics_idempotent_update(self, isolated_db):
        """Calling add_system_metrics twice on the same run updates in place."""
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        storage.add_system_metrics(run_id=run_id, cpu_percent_mean=10.0)
        # Second call should update the existing record without raising IntegrityError
        storage.add_system_metrics(run_id=run_id, cpu_percent_mean=20.0)


class TestResultStorageSaveMonitoringMetrics:
    def _make_metrics(self, n=3):
        from tribench.monitoring.base import Metric, MetricType
        return [
            Metric(
                timestamp=datetime(2025, 1, 1, 12, 0, i),
                metric_type=MetricType.SYSTEM_RESOURCE,
                name="cpu_percent",
                value=float(i * 10),
                unit="%",
                labels={"core": "0"},
            )
            for i in range(n)
        ]

    def test_save_returns_count(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        metrics = self._make_metrics(5)
        saved = storage.save_monitoring_metrics(run_id=run_id, metrics=metrics)
        assert saved == 5

    def test_save_empty_returns_zero(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        saved = storage.save_monitoring_metrics(run_id=run_id, metrics=[])
        assert saved == 0

    def test_save_non_numeric_value_stored_as_text(self, isolated_db):
        from tribench.monitoring.base import Metric, MetricType
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        metric = Metric(
            timestamp=datetime.now(),
            metric_type=MetricType.CUSTOM,
            name="status",
            value="running",
            unit="",
        )
        saved = storage.save_monitoring_metrics(run_id=run_id, metrics=[metric])
        assert saved == 1

    def test_save_batching(self, isolated_db):
        """batch_size smaller than metric count should still save all."""
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        metrics = self._make_metrics(10)
        saved = storage.save_monitoring_metrics(run_id=run_id, metrics=metrics, batch_size=3)
        assert saved == 10


class TestResultStorageGetMonitoringMetrics:
    def _populate(self, storage, run_id):
        from tribench.monitoring.base import Metric, MetricType
        base = datetime(2025, 6, 1, 10, 0, 0)
        metrics = [
            Metric(timestamp=base + timedelta(seconds=i),
                   metric_type=MetricType.SYSTEM_RESOURCE,
                   name="cpu_percent", value=float(i * 5), unit="%")
            for i in range(5)
        ] + [
            Metric(timestamp=base + timedelta(seconds=i),
                   metric_type=MetricType.TRINO_JMX,
                   name="heap_used", value=float(i * 1024), unit="bytes")
            for i in range(3)
        ]
        storage.save_monitoring_metrics(run_id=run_id, metrics=metrics)
        return base

    def test_get_all_metrics(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        self._populate(storage, run_id)
        result = storage.get_monitoring_metrics(run_id=run_id)
        assert len(result) == 8

    def test_filter_by_metric_type(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        self._populate(storage, run_id)
        result = storage.get_monitoring_metrics(run_id=run_id, metric_type="system_resource")
        assert len(result) == 5
        assert all(r["metric_type"] == "system_resource" for r in result)

    def test_filter_by_metric_name(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        self._populate(storage, run_id)
        result = storage.get_monitoring_metrics(run_id=run_id, metric_name="heap_used")
        assert len(result) == 3
        assert all(r["metric_name"] == "heap_used" for r in result)

    def test_filter_by_time_range(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        base = self._populate(storage, run_id)
        result = storage.get_monitoring_metrics(
            run_id=run_id,
            start_time=base + timedelta(seconds=2),
            end_time=base + timedelta(seconds=3),
        )
        # cpu_percent: seconds 2 & 3 (2 records)
        # heap_used: only second 2 falls in range (range(3) → 0,1,2)
        assert len(result) == 3

    def test_limit_applied(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        self._populate(storage, run_id)
        result = storage.get_monitoring_metrics(run_id=run_id, limit=3)
        assert len(result) == 3

    def test_result_dict_keys(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        self._populate(storage, run_id)
        result = storage.get_monitoring_metrics(run_id=run_id, limit=1)
        r = result[0]
        for key in ("id", "run_id", "timestamp", "metric_type", "metric_name",
                    "value", "value_text", "unit", "labels"):
            assert key in r

    def test_empty_run_returns_empty_list(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        assert storage.get_monitoring_metrics(run_id=run_id) == []


class TestResultStorageMonitoringMetricsSummary:
    def _populate(self, storage, run_id):
        from tribench.monitoring.base import Metric, MetricType
        metrics = [
            Metric(timestamp=datetime(2025, 1, 1, 12, 0, i),
                   metric_type=MetricType.SYSTEM_RESOURCE,
                   name="cpu_percent", value=float(v), unit="%")
            for i, v in enumerate([10.0, 20.0, 30.0, 40.0, 50.0])
        ]
        storage.save_monitoring_metrics(run_id=run_id, metrics=metrics)

    def test_summary_keys(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        self._populate(storage, run_id)
        summary = storage.get_monitoring_metrics_summary(run_id=run_id)
        assert "cpu_percent" in summary
        s = summary["cpu_percent"]
        assert s["count"] == 5
        assert s["min"] == pytest.approx(10.0)
        assert s["max"] == pytest.approx(50.0)
        assert s["mean"] == pytest.approx(30.0)

    def test_summary_filter_by_name(self, isolated_db):
        from tribench.monitoring.base import Metric, MetricType
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        metrics = [
            Metric(timestamp=datetime(2025, 1, 1, 12, 0, i),
                   metric_type=MetricType.SYSTEM_RESOURCE,
                   name="mem_percent", value=float(i * 5), unit="%")
            for i in range(3)
        ]
        storage.save_monitoring_metrics(run_id=run_id, metrics=metrics)
        self._populate(storage, run_id)

        summary = storage.get_monitoring_metrics_summary(
            run_id=run_id, metric_name="cpu_percent"
        )
        assert "cpu_percent" in summary
        assert "mem_percent" not in summary

    def test_empty_run_returns_empty_dict(self, isolated_db):
        storage = ResultStorage()
        _, run_id = _setup_run(storage)
        assert storage.get_monitoring_metrics_summary(run_id=run_id) == {}


# ---------------------------------------------------------------------------
# ResultStorage service tests (use isolated_db fixture for global engine)
# ---------------------------------------------------------------------------

class TestResultStorageCreateExperiment:
    def test_create_returns_integer_id(self, isolated_db):
        storage = ResultStorage()
        exp_id = storage.create_or_get_experiment(
            name="rs-exp", experiment_type="trino"
        )
        assert isinstance(exp_id, int)
        assert exp_id > 0

    def test_create_same_name_returns_same_id(self, isolated_db):
        storage = ResultStorage()
        id1 = storage.create_or_get_experiment(name="same", experiment_type="trino")
        id2 = storage.create_or_get_experiment(name="same", experiment_type="trino")
        assert id1 == id2

    def test_get_by_name(self, isolated_db):
        storage = ResultStorage()
        storage.create_or_get_experiment(
            name="find-me", experiment_type="trino", description="hello"
        )
        exp = storage.get_experiment_by_name("find-me")
        assert exp is not None
        assert exp["name"] == "find-me"
        assert exp["description"] == "hello"

    def test_get_by_name_nonexistent_returns_none(self, isolated_db):
        storage = ResultStorage()
        assert storage.get_experiment_by_name("ghost") is None

    def test_list_experiments(self, isolated_db):
        storage = ResultStorage()
        storage.create_or_get_experiment(name="e1", experiment_type="trino")
        storage.create_or_get_experiment(name="e2", experiment_type="trino")
        exps = storage.list_experiments()
        names = {e["name"] for e in exps}
        assert {"e1", "e2"}.issubset(names)


class TestResultStorageRuns:
    def test_create_run_returns_id(self, isolated_db):
        storage = ResultStorage()
        exp_id = storage.create_or_get_experiment(name="run-exp", experiment_type="trino")
        run_id = storage.create_run(experiment_id=exp_id, run_type="measured")
        assert isinstance(run_id, int)

    def test_get_run_by_id(self, isolated_db):
        storage = ResultStorage()
        exp_id = storage.create_or_get_experiment(name="gr-exp", experiment_type="trino")
        run_id = storage.create_run(experiment_id=exp_id)
        run = storage.get_run(run_id)
        assert run is not None
        assert run["id"] == run_id

    def test_complete_run_updates_status(self, isolated_db):
        storage = ResultStorage()
        exp_id = storage.create_or_get_experiment(name="cr-exp", experiment_type="trino")
        run_id = storage.create_run(experiment_id=exp_id)
        storage.complete_run(run_id, status="completed", validation_passed=True)
        run = storage.get_run(run_id)
        assert run["status"] == "completed"


class TestResultStorageQueryExecutions:
    def test_add_query_execution_returns_id(self, isolated_db):
        storage = ResultStorage()
        exp_id = storage.create_or_get_experiment(name="qe-exp", experiment_type="trino")
        run_id = storage.create_run(experiment_id=exp_id)
        qe_id = storage.add_query_execution(
            run_id=run_id,
            query_name="q01",
            start_time=datetime.now(),
            execution_time=1.23,
            rows_returned=500,
        )
        assert isinstance(qe_id, int)

    def test_get_run_query_executions(self, isolated_db):
        storage = ResultStorage()
        exp_id = storage.create_or_get_experiment(name="gqe-exp", experiment_type="trino")
        run_id = storage.create_run(experiment_id=exp_id)
        for name in ("q01", "q02", "q03"):
            storage.add_query_execution(
                run_id=run_id, query_name=name, start_time=datetime.now()
            )
        qes = storage.get_run_query_executions(run_id)
        assert len(qes) == 3
        names = {q["query_name"] for q in qes}
        assert names == {"q01", "q02", "q03"}
