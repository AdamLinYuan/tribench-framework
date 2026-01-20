"""
SQLAlchemy models for experiment results storage.

Schema Design:
- Experiment: Top-level experiment configuration and metadata
- ExperimentRun: Individual execution of an experiment (with multiple query runs)
- QueryExecution: Individual query execution within a run
- SystemMetric: Aggregated system resource metrics per run
- MonitoringMetric: Detailed time-series monitoring data (optional)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
    BigInteger,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Experiment(Base):
    """
    Represents an experiment configuration.
    
    An experiment is a benchmark workload definition (e.g., TPC-H Q1 on Iceberg).
    Multiple runs can be executed for the same experiment configuration.
    """
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    experiment_type = Column(String(100), nullable=False, index=True)  # trino, spark, etc.
    
    # Configuration
    config = Column(JSON, nullable=False)  # Full experiment configuration (YAML as JSON)
    
    # Dataset and system information
    dataset_name = Column(String(255), nullable=True, index=True)
    system_name = Column(String(100), nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Tags for categorization
    tags = Column(JSON, nullable=True)  # ["tpch", "iceberg", "sf1"]
    
    # Relationships
    runs = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_experiment_type_dataset", "experiment_type", "dataset_name"),
    )


class ExperimentRun(Base):
    """
    Represents a single execution of an experiment.
    
    One experiment can have multiple runs (e.g., 5 runs for statistical significance).
    Each run contains multiple query executions.
    """
    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Run identification
    run_number = Column(Integer, nullable=False)  # 1, 2, 3, ...
    run_type = Column(String(50), nullable=False, default="measured")  # "warmup" or "measured"
    
    # Timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default="running", index=True)  # running, completed, failed, timeout
    
    # Execution metrics (aggregated from queries)
    queries_total = Column(Integer, nullable=True)
    queries_succeeded = Column(Integer, nullable=True)
    queries_failed = Column(Integer, nullable=True)
    total_execution_time = Column(Float, nullable=True)
    
    # Validation
    validation_passed = Column(Boolean, nullable=True)
    validation_errors = Column(JSON, nullable=True)
    
    # Error information
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Monitoring
    monitoring_enabled = Column(Boolean, nullable=False, default=False)
    monitoring_file = Column(String(500), nullable=True)  # Path to monitoring JSON
    
    # Additional metadata
    run_metadata = Column(JSON, nullable=True)  # Additional run-specific metadata
    
    # Relationships
    experiment = relationship("Experiment", back_populates="runs")
    query_executions = relationship("QueryExecution", back_populates="run", cascade="all, delete-orphan")
    system_metrics = relationship("SystemMetric", back_populates="run", cascade="all, delete-orphan", uselist=False)
    
    __table_args__ = (
        Index("idx_run_experiment_number", "experiment_id", "run_number"),
        Index("idx_run_start_time", "start_time"),
        Index("idx_run_status", "status"),
    )


class QueryExecution(Base):
    """
    Represents a single query execution within an experiment run.
    
    Stores detailed metrics for each query (e.g., TPC-H Q1, Q2, etc.).
    """
    __tablename__ = "query_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Query identification
    query_name = Column(String(255), nullable=False, index=True)  # "q01", "q02", "query_1_run1"
    query_number = Column(Integer, nullable=True)  # For TPC-H/TPC-DS queries
    query_text = Column(Text, nullable=True)  # Actual SQL query (optional, can be large)
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    execution_time = Column(Float, nullable=True)  # seconds
    
    # Status
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed, timeout
    
    # Trino-specific metrics
    query_id = Column(String(255), nullable=True, index=True)  # Trino query ID
    planning_time_ms = Column(Integer, nullable=True)
    analysis_time_ms = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    cpu_time_ms = Column(BigInteger, nullable=True)
    scheduled_time_ms = Column(BigInteger, nullable=True)
    blocked_time_ms = Column(BigInteger, nullable=True)
    
    # Data processing metrics
    input_rows = Column(BigInteger, nullable=True)
    input_bytes = Column(BigInteger, nullable=True)
    output_rows = Column(BigInteger, nullable=True)
    output_bytes = Column(BigInteger, nullable=True)
    physical_input_bytes = Column(BigInteger, nullable=True)
    peak_memory_bytes = Column(BigInteger, nullable=True)
    
    # Spill metrics (HIGH priority - memory pressure analysis)
    spilled_bytes = Column(BigInteger, nullable=True)  # Total bytes spilled to disk
    
    # Parallelism metrics (MEDIUM priority - parallelism analysis)
    total_splits = Column(Integer, nullable=True)  # Total number of splits
    completed_splits = Column(Integer, nullable=True)  # Completed splits
    total_tasks = Column(Integer, nullable=True)  # Total number of tasks
    
    # Query plan tracking (MEDIUM priority - plan regression detection)
    query_plan_hash = Column(String(64), nullable=True)  # SHA256 hash of query plan
    
    # Results
    rows_returned = Column(Integer, nullable=True)
    result_checksum = Column(String(64), nullable=True)  # SHA256 for validation
    
    # Validation
    validation_passed = Column(Boolean, nullable=True)
    expected_row_count = Column(Integer, nullable=True)
    expected_checksum = Column(String(64), nullable=True)
    
    # Error information
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Metadata
    
    # Additional data
    query_metadata = Column(JSON, nullable=True)  # Query-specific metadata, query plan, etc.
    
    # Relationships
    run = relationship("ExperimentRun", back_populates="query_executions")
    
    __table_args__ = (
        Index("idx_query_run_name", "run_id", "query_name"),
        Index("idx_query_status", "status"),
        Index("idx_query_trino_id", "query_id"),
    )


class SystemMetric(Base):
    """
    Aggregated system resource metrics for an experiment run.
    
    Stores summary statistics of resource usage during the entire run.
    For detailed time-series data, see MonitoringMetric table or JSON files.
    """
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # CPU metrics (aggregated)
    cpu_percent_mean = Column(Float, nullable=True)
    cpu_percent_max = Column(Float, nullable=True)
    cpu_percent_min = Column(Float, nullable=True)
    cpu_percent_stddev = Column(Float, nullable=True)
    
    # Memory metrics (aggregated)
    memory_percent_mean = Column(Float, nullable=True)
    memory_percent_max = Column(Float, nullable=True)
    memory_bytes_mean = Column(BigInteger, nullable=True)
    memory_bytes_max = Column(BigInteger, nullable=True)
    
    # Disk I/O (totals)
    disk_read_bytes = Column(BigInteger, nullable=True)
    disk_write_bytes = Column(BigInteger, nullable=True)
    disk_read_count = Column(BigInteger, nullable=True)
    disk_write_count = Column(BigInteger, nullable=True)
    
    # Network I/O (totals)
    network_sent_bytes = Column(BigInteger, nullable=True)
    network_recv_bytes = Column(BigInteger, nullable=True)
    network_sent_packets = Column(BigInteger, nullable=True)
    network_recv_packets = Column(BigInteger, nullable=True)
    
    # Docker-specific (if available)
    container_count = Column(Integer, nullable=True)
    container_cpu_percent_mean = Column(Float, nullable=True)
    container_memory_percent_mean = Column(Float, nullable=True)
    
    # Monitoring metadata
    collection_interval_seconds = Column(Float, nullable=True)
    total_samples = Column(Integer, nullable=True)
    
    # Relationships
    run = relationship("ExperimentRun", back_populates="system_metrics")


class MonitoringMetric(Base):
    """
    Optional table for storing individual monitoring data points.
    
    For high-frequency monitoring, consider keeping JSON files and using
    this table only for critical metrics or metadata.
    """
    __tablename__ = "monitoring_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Metric identification
    metric_type = Column(String(50), nullable=False, index=True)  # system_resource, trino_jmx, query_execution
    metric_name = Column(String(255), nullable=False, index=True)
    
    # Value
    value = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)  # For non-numeric values
    unit = Column(String(50), nullable=True)
    
    # Labels/tags
    labels = Column(JSON, nullable=True)  # {"core": "0", "container": "trino"}
    
    __table_args__ = (
        Index("idx_monitoring_run_type_name", "run_id", "metric_type", "metric_name"),
        Index("idx_monitoring_timestamp", "timestamp"),
    )
