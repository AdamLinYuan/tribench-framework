# Individual Project Status Report - Semester 1

**Student**: Adam Yuan  
**Project Title**: TriBench: A Systematic Benchmarking Framework for Apache Trino  
**Date**: 12 December 2025

---

## 1. Project Description

This project develops **TriBench**, a systematic, reproducible benchmarking framework for Apache Trino, inspired by the PEEL framework architecture. Apache Trino is a distributed SQL query engine designed for querying large datasets across heterogeneous data sources. While Trino is widely used in data lakehouse architectures, there is currently no standardised framework for conducting reproducible performance benchmarks—unlike Apache Spark, which has the PEEL framework.

TriBench addresses this gap by providing:

- **Structured Experiment Definition**: YAML-based configuration for defining benchmark experiments with queries, execution parameters, and validation rules
- **Automated System Lifecycle Management**: Setup, start, stop, and teardown of Trino clusters and supporting infrastructure (MinIO, Hive Metastore, PostgreSQL)
- **Resource Monitoring**: Collection of CPU, memory, disk I/O, and Trino-specific query execution metrics
- **Result Analysis**: Structured storage and statistical analysis of benchmark results
- **Multi-Environment Deployment**: Support for both local Docker environments and Kubernetes clusters

The primary research question is: *"How can we design and implement a systematic, reproducible benchmarking framework for Apache Trino that supports executing batch workloads, monitoring resource usage, and generating structured performance reports across single-node and distributed cluster environments?"*

---

## 2. Progress Report

### Framework Architecture

TriBench follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Command Line Interface                    │
│         (tribench sys | exp | data | res | suite)           │
├─────────────────────────────────────────────────────────────┤
│                    Configuration System                      │
│     (HOCON hierarchy: reference → host → experiment)        │
├──────────────────┬──────────────────┬───────────────────────┤
│  System Manager  │ Experiment Engine│  Dataset Manager      │
│  (Trino, MinIO,  │ (Query Executor, │  (TPC-H Generator,    │
│   Hive, Postgres)│  Result Collector│   Iceberg Loader)     │
├──────────────────┴──────────────────┴───────────────────────┤
│                   Monitoring Layer                           │
│        (Resource Monitor, Trino Metrics, Alerts)            │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│           (Docker Compose | Kubernetes/Kind)                 │
└─────────────────────────────────────────────────────────────┘
```

### Configuration System

The framework uses a hierarchical HOCON-based configuration system with three layers:

1. **Reference Config** (`config/reference.conf`): Framework-wide defaults including system versions, network ports, resource limits, and path configurations
2. **Host Config** (`config/hosts/<hostname>/application.conf`): Machine-specific overrides auto-detected by hostname
3. **Experiment Config** (YAML files): Per-experiment settings that override defaults

Example experiment configuration:
```yaml
name: "tpch-iceberg-tiny"
system: "trino"
connection:
  host: "localhost"
  port: 8080
  catalog: "iceberg"
  schema: "tpch"
runs: 3
warmup_runs: 1
query_files:
  - "apps/tpch/queries/q01.sql"
  - "apps/tpch/queries/q02.sql"
  # ... all 22 TPC-H queries
```

### Experiment Suite System

Suites enable grouping related experiments with shared defaults and hierarchical configuration merging:

```yaml
name: tpch-suite
defaults:
  runs: 3
  warmup_runs: 1
  timeout_seconds: 300
experiments:
  - path: ../tpch-iceberg-tiny.yaml
    runs: 2  # Overrides suite default
```

When executed via `tribench suite run`, the framework:
1. Loads suite-level defaults
2. Merges with each experiment's configuration
3. Executes experiments sequentially with proper lifecycle management
4. Aggregates results with per-experiment and suite-level statistics

### Data Loading Pipeline

The framework implements a fast CTAS (Create Table As Select) loading strategy for TPC-H datasets:

1. **Source**: Trino's built-in `tpch` catalog generates TPC-H data on-the-fly
2. **Target**: Iceberg tables stored in MinIO (S3-compatible object storage)
3. **Performance**: ~4 seconds for tiny dataset (vs 3+ minutes with row-by-row INSERT)
4. **Column Mapping**: Automatic aliasing from Trino's short names to TPC-H standard names

### Custom Query and Dataset Support

The framework supports custom workloads beyond the built-in TPC-H benchmark. Users can define queries in three ways: inline SQL directly in YAML configuration files, references to external `.sql` files, or a combination of both. This flexibility allows benchmarking of any SQL workload against any tables accessible via Trino's catalog system. For datasets, the framework can execute queries against any existing tables in Trino—including user-created Iceberg tables, Hive tables, or data accessed through Trino's federated query connectors (e.g., PostgreSQL, MySQL, or S3). While the automated `tribench data load` command currently focuses on TPC-H data generation, users can manually create and populate custom tables via Trino SQL and then reference them in experiment configurations. Extending the data loader to support generic dataset ingestion from CSV/Parquet files is planned as a future enhancement.

### Key Achievements

| Component | Description |
|-----------|-------------|
| **CLI** | 21 commands across 4 groups (sys, exp, data, res) with dry-run and verbose modes |
| **Systems** | Trino, PostgreSQL, MinIO, Hive Metastore with Docker and Kubernetes support |
| **Benchmarks** | Full TPC-H suite (22 queries) with validation against expected row counts |
| **Iceberg** | Complete integration with Hive Metastore backend and MinIO storage |
| **Monitoring** | CPU, memory, disk I/O collection with Trino query metrics via REST API |
| **Storage** | PostgreSQL-backed result storage with CSV/JSON export |
| **Kubernetes** | Kind cluster deployment with auto-detected worker scaling |
| **Testing** | 50+ tests with 80%+ code coverage |

---

## 3. Plan of Work (Semester 2)

| Period | Work Package | Deliverables |
|--------|--------------|--------------|
| **Jan W1-2** | Analysis Engine | Statistical analysis (mean, stddev, percentiles), HTML report generation with Jinja2 templates |
| **Jan W3-4** | K8s Integration | Full experiment execution on Kind clusters, pod-level resource monitoring, user documentation |
| **Feb W1-3** | Framework Validation | Reproducibility study (10 runs, <5% variance target), scalability testing, overhead measurement |
| **Feb W4 - Mar W1** | Case Study 1 | Iceberg vs Hive table format performance comparison on TPC-H workloads |
| **Mar W2-3** | Case Study 2 | TPC-H workload characterisation (query complexity, resource patterns) |
| **Mar W4 - Apr W2** | Dissertation | Writing methodology, implementation, and evaluation chapters |
| **Apr W3-4** | Final Delivery | Code cleanup, final benchmark runs, presentation preparation |

### Key Milestones
- **End of January**: Analysis engine complete, Kubernetes fully integrated
- **End of February**: Framework validation study complete with statistical results
- **End of March**: Case studies complete, dissertation draft submitted for review
- **Mid-April**: Final submission

---

## 4. Problems and Risks

### Encountered Issues

1. **Memory Constraints**: Kind clusters running multiple Trino workers (2GB JVM heap each) exceeded Docker Desktop's default memory allocation, causing OOMKilled pods. *Resolution*: Documented requirement for 12-16GB Docker memory; reduced default worker count.

2. **Data Loading Performance**: Initial implementation used row-by-row INSERT statements, taking 3+ minutes for even tiny datasets. *Resolution*: Implemented CTAS loading from Trino's built-in `tpch` catalog, reducing load time to ~4 seconds.

3. **Schema Compatibility**: Trino's `tpch` connector uses abbreviated column names (e.g., `shipdate`) while TPC-H queries expect prefixed names (e.g., `l_shipdate`). *Resolution*: Implemented automatic column mapping with SQL aliases during CTAS.

### Anticipated Risks

| Risk | Likelihood | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| Limited cluster access for distributed validation | Medium | High | Primary testing on Kind; request School cluster access in January |
| Dissertation writing time pressure | Medium | High | Begin methodology chapter in January; maintain weekly writing schedule |
| Complex distributed monitoring | Low | Medium | Focus on essential metrics (CPU, memory, query time); defer Prometheus integration |

### Dependencies
- Docker Desktop with 12-16GB memory allocation for Kubernetes testing
- Access to multi-node cluster for production-scale validation (optional but beneficial)
- Supervisor feedback on case study design by end of January

---

*Report prepared: 12 December 2025*
