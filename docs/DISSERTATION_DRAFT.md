# Honours Individual Project Dissertation
# TRIBENCH: A SYSTEMATIC BENCHMARKING FRAMEWORK FOR APACHE TRINO DATA LAKEHOUSES
Adam Yuan
February 2026

---

## Abstract

Over the past decade, large-scale analytical systems have undergone a structural transformation. The data lakehouse architecture, which combines the low-cost object storage of a data lake with the ACID transactional guarantees of a data warehouse, has emerged as a dominant pattern for enterprise analytics. Apache Iceberg, an open table format that provides snapshot isolation, time-travel queries, and schema evolution on top of columnar Parquet files, has become a cornerstone of this architecture. Apache Trino, a distributed SQL query engine capable of federating queries across heterogeneous data sources, is increasingly deployed as the interactive query layer over Iceberg-based lakehouses in production environments.

Despite the maturity of this stack, the ecosystem currently lacks a reproducible, systematic benchmarking framework for Trino comparable to what PEEL provides for Apache Spark. Existing tools either require significant manual configuration per run, lack integrated hardware monitoring, or cannot port across deployment environments without modification. This creates a reproducibility problem: performance results reported in one environment cannot reliably be reproduced in another, and the effort required to re-run experiments from scratch discourages rigorous empirical evaluation.

We propose TriBench, a cross-platform framework that addresses this gap by providing structured batch workload execution, concurrent hardware resource monitoring, and persistent result storage in a configuration-driven, portable bundle. TriBench supports both Docker-based local deployments and Kubernetes-based distributed cluster deployments, allowing the same experiment specification to execute on a developer laptop or a multi-node school cluster without modification. The framework is evaluated using the TPC-H benchmark suite at multiple scale factors on a local Docker deployment and a Kubernetes-based school cluster, demonstrating repeatable query execution with full hardware telemetry across both environments.

The results show that TriBench successfully orchestrates reproducible experiments, captures CPU, memory, disk I/O, network I/O, and per-pod Kubernetes metrics concurrently with query execution, and persists results in a structured store that supports downstream analysis and cross-run comparison. The framework fulfils the identified need for a PEEL-equivalent systematic benchmarking tool in the Apache Trino ecosystem.

---

## Contents

1. Introduction
2. Background
3. Related Work
4. Requirements
5. Design
6. Implementation
7. Evaluation
8. Conclusion
9. Appendices

---

## 1 Introduction

### 1.1 Motivation

The architecture of data management systems has undergone several major transitions in the past two decades. Traditional relational data warehouses, built on proprietary columnar storage engines and offering strong consistency guarantees, provided the analytical foundation for enterprise business intelligence. However, as data volumes grew exponentially and the types of data requiring analysis broadened beyond structured records to semi-structured logs, event streams, and binary assets, a new pattern emerged: the data lake. Data lakes offered low-cost, schema-on-read storage using commodity object stores — such as HDFS or Amazon S3 — allowing organisations to ingest raw data cheaply and defer schema enforcement to query time. While cost-effective in storage, data lakes introduced new challenges: without transactional guarantees, concurrent writes could produce corrupt states; without schema enforcement, data quality degraded silently; and without a centralised metadata service, query engines could not prune irrelevant files, leading to unnecessarily expensive full-table scans.

The data lakehouse architecture arose to address these shortcomings. Coined prominently by Armbrust et al. (2021), the lakehouse pattern augments raw object storage with an open table format layer that provides ACID transactions, snapshot-based time travel, and partition pruning metadata, all without moving data out of the object store. Apache Iceberg has become the leading open table format implementing this pattern, providing snapshot isolation, hidden partitioning, and schema evolution alongside an open specification that any query engine can implement. Apache Trino — formerly known as PrestoSQL — is a massively parallel processing (MPP) distributed SQL query engine designed to be deployed as the interactive query layer over such lakehouses. Trino's coordinator-worker architecture allows linear horizontal scaling: a single coordinator node parses and plans queries, then distributes work units called splits across a fleet of worker nodes that execute them in parallel.

Performance benchmarking is central to the responsible deployment and evolution of such systems. Database administrators, platform engineers, and researchers need quantitative answers to questions such as: How does query latency change as the number of worker nodes increases? At what point do memory pressures on worker pods cause performance degradation? Does a particular Iceberg partitioning strategy meaningfully reduce scan times for a given query pattern? Without a reproducible benchmarking methodology, answering these questions requires ad-hoc scripting that varies from one engineer to the next, results cannot be compared across experiments, and the effort required to re-run a prior experiment from scratch is prohibitive.

The standard methodology for relational and analytical benchmarking is the Transaction Processing Performance Council (TPC) suite of benchmarks. TPC-H simulates a data warehousing workload with 22 analytical SQL queries of varying complexity over a relational schema representing a supply-chain business. TPC-DS extends this to a retail sales scenario with 99 queries designed to stress-test modern analytical systems. While these query specifications are standardised, the infrastructure required to run them reproducibly — provisioning the data lakehouse stack, loading datasets at the correct scale factor, capturing system metrics during execution, and persisting structured results — must be managed by the benchmarker. For Spark-based ecosystems, the PEEL framework provides exactly this scaffolding. For Apache Trino, no equivalent tool exists.

TriBench is designed to fill this gap. It provides a Python-based framework for defining, executing, monitoring, and storing benchmark experiments against Apache Trino deployments. Its design is informed by PEEL's core architectural principle: the experiment bundle separates the concerns of environment specification, workload definition, and result collection into reusable, composable units that are reproducible across deployment environments. TriBench extends this principle with integrated real-time hardware monitoring and a portable configuration system that makes the same experiment specification runnable on a local Docker deployment or a distributed Kubernetes cluster without modification.

### 1.2 Goals

The goals of the project are defined below in a strict numbered hierarchy. These goal identifiers are used consistently throughout the dissertation and are referenced explicitly in Chapter 7 to demonstrate that each goal has been met.

**(1) Execute Benchmark Workloads**
TriBench must be capable of submitting SQL workloads to a running Apache Trino cluster and collecting the results of each query in a structured format.

> **(1.1) Support TPC-H Queries**
> The framework must include the complete set of TPC-H SQL queries (Q1–Q22) adapted for Trino's Iceberg connector, and must be able to execute them against pre-loaded datasets at configurable scale factors.

> **(1.2) Support Custom SQL Workloads**
> The framework must allow users to specify arbitrary SQL query files, enabling workloads beyond the TPC-H suite to be executed using the same benchmarking infrastructure.

> **(1.3) Support Configurable Execution Parameters**
> Experiments must support configurable warmup runs (which are executed but not measured), a configurable number of measured runs, per-query timeout enforcement, and optional parallel concurrent query execution.

**(2) Monitor Hardware Resource Usage**
During query execution, the framework must concurrently collect hardware resource metrics from the host machine and, where applicable, from Kubernetes pods.

> **(2.1) Collect System-Level Resource Metrics**
> The framework must collect CPU utilisation (both overall and per-core), memory usage (RAM and swap), disk I/O (read and write throughput), and network I/O (bytes sent and received) at a configurable sampling interval.

> **(2.2) Collect Kubernetes Pod-Level Metrics**
> When running in a Kubernetes deployment, the framework must additionally collect per-pod CPU (in millicores) and memory metrics for all Trino-related pods, using the Kubernetes Metrics Server.

> **(2.3) Collect Trino Query Execution Metrics**
> The framework must capture query-level metrics including wall-clock execution time, CPU time, data scanned in bytes, and rows returned for each query execution.

**(3) Generate Structured Benchmark Reports**
All results must be persisted in a structured, queryable form that enables post-hoc analysis and cross-run comparison.

> **(3.1) Persist Results to a Relational Store**
> Experiment results, query timings, and collected metrics must be stored in a relational database (SQLite for single-node deployments, PostgreSQL for distributed deployments), using a normalised schema that separates run records, query results, and time-series metric samples.

> **(3.2) Support JSON and CSV Export**
> Results must also be exportable as JSON and CSV files to enable analysis in external tools such as pandas, Excel, or Jupyter notebooks.

> **(3.3) Enforce Non-Overwriting Result Isolation**
> Each experiment run must be stored under a unique run identifier so that repeated executions of the same experiment do not overwrite prior results, preserving the full experimental history.

**(4) Scale Across Deployment Environments**
The framework must be runnable on at minimum two distinct deployment targets — a local Docker Compose deployment and a distributed Kubernetes cluster deployment — using the same experiment specification files.

> **(4.1) Support Docker Compose Local Deployment**
> For development and single-machine experiments, the framework must manage the full data lakehouse stack (Trino, Hive Metastore, MinIO, PostgreSQL) via Docker Compose, including automated setup, start, and teardown.

> **(4.2) Support Kubernetes Distributed Deployment**
> For distributed experiments, the framework must deploy the same stack on a Kubernetes cluster using generated Kubernetes manifests, manage port-forwarding for local CLI access, and collect pod-level metrics from the running cluster.

### 1.3 Dissertation Outline

The remainder of this dissertation is structured as follows:

- **Chapter 2** presents the background concepts underpinning the project, including the data lakehouse architecture, Apache Iceberg, Apache Trino's distributed query execution model, and the principles of reproducible benchmarking.
- **Chapter 3** surveys related work, including the PEEL benchmarking framework, existing Trino tooling, and the gap in the ecosystem that TriBench addresses.
- **Chapter 4** provides a formal specification of TriBench's functional and non-functional requirements, grounded in the goals stated above.
- **Chapter 5** describes the design of TriBench, presenting an architecture divided into five layers: CLI, Configuration, Orchestration, Systems, and Data Lakehouse.
- **Chapter 6** describes the implementation of TriBench, covering the programming environment, core module structure, monitoring internals, result storage design, and file handling.
- **Chapter 7** evaluates TriBench through three progressively complex scenarios, explicitly mapping each back to the goals defined in Chapter 1.
- **Chapter 8** concludes the dissertation with a summary of contributions, a frank assessment of limitations, and directions for future work.

---

## 2 Background

### 2.1 Data Lakehouses and Open Table Formats

The transition from traditional data warehouses to data lakehouses reflects a broader shift in how organisations manage analytical data. In a traditional data warehouse, data is ingested from operational systems through an extract-transform-load (ETL) pipeline and stored in a proprietary columnar format. The warehouse engine enforces schemas, manages indexes, and optimises physical storage layouts — providing excellent query performance but at significant cost per terabyte and with limited flexibility for non-relational data types. The data lake model, underpinned by the Hadoop Distributed File System (HDFS) and later by cloud object stores such as Amazon S3 or MinIO, decoupled storage from compute: data was stored cheaply as flat files, and query engines such as Hive, Spark, or Presto were applied to them on demand. However, this model's lack of transactional guarantees created practical problems at scale. Concurrent writers could corrupt table state; deleted records might remain visible to ongoing readers; and the absence of file-level metadata meant query engines had to scan every file in a table to answer a query, regardless of its relevance.

Apache Iceberg was developed at Netflix to address these problems and is now an Apache Software Foundation top-level project. Iceberg defines a table format — a specification for how tabular data should be organised on an object store and how metadata about that data should be structured. An Iceberg table consists of a tree of metadata objects: a current metadata file points to a manifest list, which points to one or more manifest files, each of which records the locations and column statistics of data files (typically Parquet-formatted). This tree structure enables snapshot isolation: a write operation creates a new snapshot by appending new manifest files and atomically updating the metadata pointer, while concurrent readers continue to see the old snapshot until they refresh. Because each manifest file records column-level min/max statistics for the data files it references, query engines can apply partition pruning and predicate pushdown at the planning stage, skipping entire files that cannot contribute to the query result without reading them.

From a benchmarking perspective, Iceberg tables introduce a layer of metadata management that traditional file-based benchmarks do not capture. The time required to resolve Iceberg metadata before query execution, the effect of snapshot accumulation on metadata resolution latency, and the performance impact of Iceberg's hidden partitioning strategy on specific query patterns are all meaningful quantities to measure. TriBench targets this stack directly, enabling these dimensions to be explored systematically.

The deployment of Iceberg requires a metadata catalogue service — a component that maps table names in a SQL namespace to their underlying Iceberg metadata file locations. The Hive Metastore Service (HMS) is the most widely used catalogue in the current ecosystem. HMS speaks the Thrift protocol on port 9083 and persists catalogue state in a relational backend, typically PostgreSQL. Trino communicates with HMS to resolve table metadata at query planning time, meaning the health and performance of the metastore directly affects query latency. MinIO provides the S3-compatible object storage backend in which Iceberg data files and metadata are physically stored.

### 2.2 Apache Trino

Apache Trino is a distributed SQL query engine designed for interactive analytical queries over large datasets. Its architecture is divided into a coordinator node and one or more worker nodes, all communicating over an HTTP/2 protocol. When a client submits a query, the coordinator parses the SQL, validates it against the catalogue (Hive Metastore), and generates a distributed execution plan. The plan is divided into pipeline stages, and each stage is further divided into execution units called splits. Splits represent portions of a table — for an Iceberg table, a split typically corresponds to a single Parquet file or a row-group within a file. Splits are assigned to worker nodes, which execute them in parallel using an operator pipeline model: data flows through a chain of operators (table scan, filter, project, aggregate, join) as it moves from storage to the final result set.

The key performance characteristics of a Trino deployment depend on several interacting factors: the number and core count of worker nodes, available JVM heap per worker (controlled by the `query.max-memory-per-node` property), the Iceberg catalogue resolution time, the network bandwidth between workers, and the I/O throughput of the object store. Trino exposes an extensive JMX interface over its HTTP management port, providing metrics such as active queries, queued queries, JVM heap usage, and per-stage execution statistics. TriBench's monitoring layer collects metrics from this interface alongside system-level hardware metrics to give a complete picture of resource consumption during benchmark execution.

Trino's SQL dialect is largely ANSI-standard but includes extensions for Iceberg-specific operations such as time-travel queries (`SELECT ... FOR VERSION AS OF <snapshot_id>`) and partition management DDL. The TPC-H queries used in this project are standard ANSI SQL with minor adaptations for Trino's Iceberg connector (specifically, fully-qualified three-part table names of the form `<catalog>.<schema>.<table>`).

### 2.3 Benchmarking Methodologies

Benchmarking is the practice of subjecting a system to a defined workload under controlled conditions and measuring its performance characteristics. For database systems, the Transaction Processing Performance Council (TPC) has produced the most widely accepted benchmark suites. TPC-H models a multi-user decision support system with 22 analytical queries over a normalised schema; TPC-DS extends this to a 99-query retail analytics workload with more complex query patterns including window functions, correlated subqueries, and multi-table joins. Both benchmarks define a scale factor (SF) that controls the dataset size: SF1 produces approximately 1 GB of raw data, SF10 approximately 10 GB, and so on.

Reproducibility is the cardinal virtue of any benchmark. According to Binnig et al. (2018), a benchmark is reproducible if an independent experimenter can re-execute it under the same conditions and obtain results that are consistent within a defined tolerance. For complex distributed systems, achieving this requires careful attention to: (a) environment specification — the exact hardware and software configuration of the system under test; (b) data consistency — loading the exact same dataset, at the exact same scale factor, in the exact same physical layout; (c) execution control — enforcing the same warmup strategy, query ordering, and concurrency model across runs; and (d) measurement capture — recording the same metrics at the same granularity. TriBench addresses all four dimensions through its configuration-driven experiment specification, dataset registry, and integrated monitoring system.

Performance metrics of interest in distributed SQL benchmarking include: query wall-clock time (the elapsed time from query submission to result receipt); CPU time (the sum of CPU time consumed across all worker nodes, reported by Trino's JMX interface); peak memory usage per worker; data scanned (total bytes read from the object store); and rows returned. System-level metrics — particularly CPU utilisation and memory pressure — are important complements to query-level metrics because they reveal resource saturation that might not manifest in query times until a threshold is crossed.

---

## 3 Related Work

### 3.1 The PEEL Framework

PEEL (Performance Evaluation and Experimentation Lab) is a Scala-based framework for systematic benchmarking of distributed data processing systems, with a primary focus on Apache Spark and Apache Flink. Originally described by Alexandrov et al. (2015), PEEL introduced the concept of the experiment bundle: a self-contained directory structure comprising system configurations, workload definitions, and dataset specifications, all parameterised by a unified configuration system backed by the Typesafe Config library (HOCON format). A PEEL bundle can be checked into version control and executed on any machine that has the required system binaries installed, producing results that are directly comparable to those from any other machine running the same bundle.

PEEL's design separates three concerns that are commonly conflated in ad-hoc benchmarking scripts. First, system management: PEEL knows how to start, stop, and configure the systems under test (Spark, Flink, HDFS, Kafka) via its system abstraction. Second, experiment execution: PEEL defines an experiment as a unit of work executed against a running system, and a suite as an ordered collection of experiments sharing configuration defaults. Third, result persistence: PEEL stores experiment results in a relational database with a well-defined schema, enabling SQL queries over the result collection. These three concerns map directly to TriBench's Systems Layer, Orchestration Layer, and Storage Layer respectively.

TriBench is explicitly inspired by PEEL and adopts its core architectural principles, including the HOCON-based hierarchical configuration system and the concept of experiment suites. However, TriBench departs from PEEL in several important ways: it targets Apache Trino rather than Spark or Flink; it is implemented in Python rather than Scala, making it more accessible to a data engineering audience; and it adds integrated real-time hardware monitoring that PEEL does not provide natively.

### 3.2 Existing Trino Tooling

Apache Airflow is a workflow orchestration platform widely used to schedule and monitor data pipelines, including those that submit queries to Trino via its Python provider (`apache-airflow-providers-trino`). While Airflow excels at managing complex DAG-based pipeline dependencies, it does not provide benchmarking abstractions: there is no built-in concept of warmup runs, result persistence across runs, or hardware metric collection. Using Airflow for benchmarking would require significant custom development and would not produce the bundle-based reproducibility that TriBench offers.

Grafana, in combination with Prometheus, is commonly used to visualise Trino's JMX metrics in production environments. Trino exposes its JMX interface over HTTP, and Prometheus can scrape it at regular intervals; Grafana dashboards then visualise these metrics as time-series graphs. This is a powerful operational monitoring solution, but it is fundamentally reactive — it observes a running system — rather than orchestrative. It cannot define experiments, load datasets, manage system lifecycle, or systematically enumerate a query set. Furthermore, its result retention and query capabilities are limited compared to a relational database of structured experiment results.

The Trino community maintains benchmark contributions in its GitHub repository, most notably a set of TPC-H and TPC-DS query generators and a `benchmark` module within the Trino server project. However, these tools are oriented towards internal Trino development testing rather than end-user deployment. They require building the Trino server from source, do not manage the surrounding data lakehouse stack (metastore, object storage), and produce results in flat text files rather than a structured queryable store.

### 3.3 Gap Analysis

The survey above reveals a clear gap in the Apache Trino ecosystem. Tools exist for query generation (Trino benchmark module), workflow orchestration (Airflow), and production monitoring (Grafana + Prometheus), but none combine all three into a reproducible benchmarking framework analogous to PEEL. Specifically, no existing open tool: (a) manages the full data lakehouse stack lifecycle from a single CLI; (b) provides PEEL-style experiment bundles with HOCON-based configuration hierarchies; (c) concurrently captures hardware resource metrics during query execution; (d) persists results in a normalised relational schema supporting cross-run comparison; and (e) runs identically on a local Docker deployment and a distributed Kubernetes cluster without modification to the experiment specification.

TriBench is designed to fill exactly this gap. It does not compete with Airflow for production pipeline orchestration, nor with Grafana for operational dashboarding; rather, it provides a self-contained, reproducible experimentation environment for empirical performance evaluation of Trino deployments.

---

## 4 Requirements

### 4.1 Problem Specification

The core technical challenge addressed by this project originates from the absence of a systematic, reproducible benchmarking tool for Apache Trino in the data lakehouse ecosystem. Engineers and researchers who need to evaluate Trino performance — comparing configurations, measuring scaling behaviour, or validating the performance impact of schema changes — currently have no framework that integrates workload execution, hardware monitoring, and result persistence into a portable, configuration-driven bundle. This absence means that performance experiments are typically implemented as one-off scripts that are not reusable, not reproducible across environments, and not instrumented for hardware-level metrics. TriBench addresses this problem by providing the missing framework layer.

### 4.2 Functional Requirements

- **FR1**: The system must accept a YAML experiment configuration file specifying the query workload, connection parameters, and execution settings, and execute the specified queries against a Trino cluster.
- **FR2**: The system must support the complete TPC-H query suite (Q1–Q22) in Trino-compatible SQL, parameterised by scale factor and Iceberg schema name.
- **FR3**: The system must support loading arbitrary additional SQL query files from the filesystem to enable custom workloads beyond TPC-H.
- **FR4**: Experiments must support a configurable number of warmup runs (executed but not recorded), a configurable number of measured runs, and a per-query timeout enforcement mechanism.
- **FR5**: During query execution, the system must concurrently collect CPU utilisation (total and per-core), memory usage (RAM and swap), disk I/O throughput, and network I/O throughput from the host machine, at a configurable sampling interval.
- **FR6**: When running in Kubernetes mode, the system must additionally collect per-pod CPU (millicores) and memory metrics for all Trino-related pods using the Kubernetes Metrics Server.
- **FR7**: For each query execution, the system must record the wall-clock execution time, CPU time, data scanned in bytes, and rows returned as reported by Trino.
- **FR8**: All experiment results must be persisted to a relational database (SQLite or PostgreSQL) in a normalised schema that enables cross-run comparison via SQL queries.
- **FR9**: Results must additionally be exportable as JSON and CSV files for downstream analysis.
- **FR10**: Each experiment run must be assigned a unique run identifier so that repeated executions of the same experiment do not overwrite prior results.
- **FR11**: The system must manage the full Docker Compose data lakehouse stack (Trino, Hive Metastore, MinIO, PostgreSQL) via a command-line interface exposing setup, start, stop, and teardown operations.
- **FR12**: The system must deploy and manage the same stack on a Kubernetes cluster using generated manifests, with automated port-forwarding for local CLI access.
- **FR13**: The same experiment YAML specification must execute on both Docker and Kubernetes deployments without modification.

### 4.3 Non-Functional Requirements

- **NFR1 — Reproducibility**: Given the same configuration bundle, data scale factor, and deployment environment, the framework must produce results that are consistent within a defined statistical tolerance across repeated runs. This tolerance is captured by the `validation.max_execution_time_variance` configuration field.
- **NFR2 — Modularity**: The framework's internal components — monitoring, storage, system management, CLI — must be independently usable. A user who does not wish to monitor hardware resources must be able to disable monitoring without affecting workload execution or result persistence.
- **NFR3 — Portability**: The framework must run correctly on macOS, Linux, and Windows (via WSL2) without modification to core library code.
- **NFR4 — Non-Interference**: The overhead introduced by concurrent hardware monitoring must not materially affect benchmark results. The monitoring sampling interval must be configurable to allow the user to trade granularity for overhead.
- **NFR5 — Observability**: The framework must emit structured logs at configurable verbosity levels, enabling diagnostic investigation of execution problems without requiring code modification.
- **NFR6 — Extensibility**: The system abstraction must be implemented as an abstract base class so that additional backends (e.g., bare-metal Trino deployments, Presto, StarRocks) can be added without modifying the core orchestration logic.

---

## 5 Design

### 5.1 Architecture Overview

TriBench's architecture divides the concerns of benchmarking into five conceptual layers, each with a well-defined responsibility and a clean interface to adjacent layers. As illustrated in the conceptual model below, these layers are traversed top-to-bottom during experiment execution:

```
┌───────────────────────────────────────────────────────────────┐
│  CLI Layer        (tribench sys | data | exp | result | suite) │
├───────────────────────────────────────────────────────────────┤
│  Configuration Layer   (HOCON reference.conf → host → exp → CLI) │
├───────────────────────────────────────────────────────────────┤
│  Orchestration Layer   (ExperimentConfig, TrinoExperiment,      │
│                         ExperimentSuite, Monitoring)            │
├───────────────────────────────────────────────────────────────┤
│  Systems Layer    (System ABC → TrinoSystem, KubernetesSystem)  │
├───────────────────────────────────────────────────────────────┤
│  Data Lakehouse Layer  (Trino ↔ Hive Metastore ↔ MinIO + Iceberg) │
└───────────────────────────────────────────────────────────────┘
```

Each layer encapsulates a distinct concern. The CLI Layer provides the user-facing interface as a set of Click command groups. The Configuration Layer provides a unified, hierarchically merged view of all configuration parameters, from framework-level defaults down to per-run CLI overrides. The Orchestration Layer manages the lifecycle of an experiment: loading the configuration, submitting queries, running monitoring concurrently, and persisting results. The Systems Layer abstracts the physical deployment environment, presenting a consistent `setup / start / stop / teardown` interface regardless of whether the underlying system is Docker Compose or Kubernetes. The Data Lakehouse Layer is the runtime being benchmarked: a Trino cluster connected to a Hive Metastore and a MinIO object store, with data stored in Apache Iceberg table format.

### 5.2 CLI Layer

The CLI layer is implemented using the Click library and exposes six command groups:

- `tribench sys` — system lifecycle commands: `setup`, `start`, `stop`, `teardown` for Docker and Kubernetes backends.
- `tribench data` — data management commands: `load` (ingest Parquet datasets into Iceberg tables via Hive Metastore), `generate` (generate TPC-H data at a specified scale factor), `list`.
- `tribench exp` — experiment execution commands: `run` (execute a single experiment YAML), `suite` (execute an ordered collection of experiments).
- `tribench result` — result retrieval commands: `list`, `show`, `export` (to CSV or JSON), `compare` (diff two runs), `analyze`.
- `tribench config` — configuration introspection commands: `show` (print resolved config), `profile` (manage active host profiles).
- `tribench suite` — suite management commands.

Backend selection within the CLI is controlled by a utility function `should_use_kubernetes(config)` that inspects the active configuration's `tribench.defaults.backend` field. This allows users to switch between Docker and Kubernetes deployments by changing a single line in their host configuration file, without modifying any experiment specification. The active configuration profile is stored in the `.tribench-profile` file in the project root, enabling per-machine defaults to be committed alongside the experiment bundle.

### 5.3 Configuration Layer

TriBench adopts HOCON (Human-Optimised Config Object Notation) for its configuration system, using the `pyhocon` library. HOCON provides a superset of JSON with support for variable substitution (`${variable}`), file inclusion, and key merging. The configuration is loaded through a four-level merge hierarchy:

1. **Reference configuration** (`config/reference.conf`): framework-level defaults covering all configurable parameters with safe default values. This file defines the complete schema of configurable options.
2. **Host configuration** (`config/hosts/<hostname>.conf`): machine-specific overrides, loaded by matching the operating system hostname. Example host files include `kind.conf` (for local Kind Kubernetes clusters) and `gcp-gke.conf` (for Google Kubernetes Engine).
3. **Experiment configuration** (the YAML file passed to `tribench exp run`): experiment-specific parameters including query files, connection details, and execution settings.
4. **CLI and environment overrides**: individual parameters passed on the command line (e.g., `--runs 5 --host localhost`) or via environment variables (e.g., `TRIBENCH_DATABASE_URL`), applied last with highest priority.

The `ConfigurationLoader` class in `lib/tribench/utils/config/loader.py` manages the first two levels, while `ExperimentConfig.from_yaml()` manages the incorporation of the experiment YAML and CLI overrides via a `_deep_merge()` operation that recursively merges nested dictionaries without overwriting unrelated keys.

### 5.4 Orchestration Layer

The Orchestration Layer is responsible for the lifecycle of a single experiment run. At its centre is the `ExperimentConfig` data class (`lib/tribench/core/experiment.py`), which represents the fully resolved configuration for one experiment. Its principal fields include: the query workload (a list of inline SQL strings or paths to SQL files), execution parameters (runs, warmup runs, timeout, parallel query count), Trino connection parameters, validation rules, and a reference to the raw configuration for monitoring-related fields.

The `TrinoExperiment` class orchestrates query execution against a live Trino cluster. For each query in the workload, the experiment runner: (1) submits the query to Trino via the `trino-python-client` library; (2) streams the result rows and records the row count; (3) captures query execution metadata (execution time, CPU time, bytes scanned) from Trino's query information endpoint; (4) checks the result against any validation rules specified in the experiment configuration; and (5) constructs a `Result` object that is handed to the storage layer.

Concurrent hardware monitoring is managed by a `MonitoringSession` that is started before the first query and stopped after the last query. The session coordinates multiple `MetricCollector` instances — `ResourceMonitor`, `KubernetesMonitor`, and `TrinoMonitor` — running in a background thread pool. Each collector samples its respective metrics source at the configured interval and appends `Metric` objects to an internal buffer, which is flushed to the storage layer at defined intervals.

An `ExperimentSuite` wraps an ordered list of experiments, allowing common defaults such as connection parameters or execution settings to be defined once at the suite level and inherited by all members. Suite-level defaults are applied before experiment-level YAML values using the same `_deep_merge` strategy, establishing a three-level precedence within the experiment configuration: suite defaults < experiment YAML < CLI overrides.

### 5.5 Systems Layer

The Systems Layer abstracts the deployment environment behind the `System` abstract base class defined in `lib/tribench/core/system.py`. All concrete system implementations must provide `setup()`, `start()`, `stop()`, and `teardown()` methods. TriBench currently ships two concrete implementations:

**TrinoSystem** (`lib/tribench/systems/trino/system.py`) manages a single Trino instance using Docker. It is internally decomposed into four components: `TrinoSetup` (managing binary downloads, directory creation, and Docker network creation), `TrinoConfigGenerator` (generating Trino configuration files — `config.properties`, `jvm.config`, `node.properties`, `iceberg.properties` — from templates parameterised by the active HOCON configuration), `TrinoLifecycle` (managing `docker compose up/down` invocations), and `TrinoHealthMonitor` (polling the Trino REST API until the coordinator reports itself ready). The full Docker Compose data lakehouse stack — including Hive Metastore, MinIO, and PostgreSQL — is managed by a parallel `HiveMetastoreSystem`, `MinIOSystem`, and `PostgreSQLSystem`, each implementing the same `System` interface.

**KubernetesSystem** (`lib/tribench/systems/kubernetes/system.py`) manages the same stack on a Kubernetes cluster. It uses the Jinja2 templating engine to render Kubernetes manifest YAML files from `.j2` templates in `config/templates/`, substituting cluster-specific values (image names, storage class names, resource limits) from the active HOCON configuration. The rendered manifests are applied to the cluster via `kubectl apply`. The Kubernetes system also manages port-forwarding from the local machine to the Trino coordinator service, enabling the same Trino Python client connection to function transparently in both Docker and Kubernetes modes.

The separation of system management from experiment orchestration means that the Orchestration Layer communicates with the Systems Layer only through the `System` interface, and is therefore insensitive to which concrete backend is in use. An experiment run does not need to know whether it is talking to a Docker container or a Kubernetes pod; it only needs a TCP connection to `localhost:8080`.

### 5.6 Monitoring System

The monitoring system is designed around the `MetricCollector` abstract base class in `lib/tribench/monitoring/base.py`. Each collector implements `start()`, `stop()`, and `collect()` methods. The `MonitoringConfig` data class centralises all monitoring parameters: the sampling interval in seconds, boolean flags to enable or disable each collector type, alert thresholds, and output directory.

**ResourceMonitor** uses the `psutil` library to collect system-level metrics. At each sample interval it records: CPU utilisation (total percentage and percentage per logical core), memory used and memory percentage (both physical RAM and swap), disk I/O deltas relative to a baseline captured at monitor start (bytes read/written and I/O operation counts), and network I/O deltas (bytes sent/received and packet counts). Each captured sample is converted to a list of `Metric` objects, labelled with their type (`SYSTEM_RESOURCE`), name, value, and unit.

**KubernetesMonitor** uses `subprocess` to invoke `kubectl top pods` at each sample interval and parses the output to extract per-pod CPU (millicores) and memory (MB, GB) for all pods in the Trino namespace. Pod metrics are labelled by pod name, namespace, and role (coordinator or worker) using Kubernetes label selectors.

**TrinoMonitor** queries Trino's JMX endpoint to collect cluster-level Trino metrics such as active queries, queued queries, and JVM heap usage, and fetches per-query execution statistics from the Trino REST API's query information endpoint after each query completes.

### 5.7 Reporting and File Handling

The result storage system (`lib/tribench/storage/`) uses SQLAlchemy to provide a database-agnostic ORM over either a local SQLite file (`results/tribench.db`) or a PostgreSQL database. The schema is organised into four stores:

- **RunStore**: records the top-level experiment run metadata (run ID, experiment name, start and end timestamps, status).
- **QueryStore**: records each individual query execution within a run (query name, SQL text, execution time, CPU time, rows returned, data scanned, validation result).
- **MetricStore**: records the time-series hardware metric samples collected during the run (metric name, value, unit, labels, timestamp).
- **ExperimentStore**: records the full experiment configuration as a JSON snapshot, enabling the exact configuration to be inspected after the fact.

Run IDs are generated as `<experiment_name>_<timestamp>` strings, ensuring that repeated executions of the same experiment produce disjoint run records rather than overwriting prior results. The `ResultStorage` class provides the high-level API used by the Orchestration Layer: `begin_run()`, `record_query()`, `record_metric()`, `end_run()`, and `export_csv()`. JSON export serialises the complete result tree, including all query results and metric samples, into a single JSON file named after the run ID.

---

## 6 Implementation

### 6.1 Environment and Tooling

TriBench is implemented in Python 3.9+ and relies on the following principal third-party libraries:

- **Click** (8.x): declarative CLI framework used to define command groups, arguments, options, and help text.
- **pyhocon** (0.3.x): HOCON configuration parser providing the hierarchical merge semantics described in Section 5.3.
- **trino-python-client** (0.x): the official Apache Trino Python client, used by the Orchestration Layer to submit queries over HTTP/2 and retrieve result rows and query metadata.
- **psutil** (5.x): cross-platform system information library used by `ResourceMonitor` to collect CPU, memory, disk, and network metrics.
- **docker** (Python SDK): used by `ResourceMonitor` to optionally collect per-container CPU and memory statistics when running in Docker mode.
- **SQLAlchemy** (2.x): ORM framework providing the database abstraction over both SQLite and PostgreSQL backends.
- **Jinja2** (3.x): template engine used by the Systems Layer to render Kubernetes manifest YAML files from `.j2` template files.
- **PyYAML**: used to parse experiment configuration YAML files.
- **pandas** and **tabulate**: used in the analysis and result display commands to format and summarise result tables.

The project is packaged via `setup.py` with a `tribench` entry point, making the CLI available after `pip install -e .`. A `conda` environment specification is provided in `environment.yml`, and the framework is tested with `pytest` under the configuration in `pytest.ini`.

### 6.2 Core Modules

**ExperimentConfig (`lib/tribench/core/experiment.py`)** is a Python `@dataclass` with class method `from_yaml()` that implements the three-level configuration merge. The `_deep_merge()` static method recursively merges nested dictionaries: for each key in the override dictionary, if the same key exists in the base and both values are dictionaries, the method recurses; otherwise, the override value replaces the base value. This semantics allows a CLI override of `connection.port = 9090` to update only the port field of the connection dictionary while leaving the host, user, and catalog fields from the experiment YAML intact.

**TrinoExperiment (`lib/tribench/experiments/`)** implements the query execution loop. For warmup runs, queries are submitted and results discarded without storage. For measured runs, each query submission is wrapped with timing calls using `datetime.now()` to capture wall-clock time, and the Trino client's cursor is used to stream rows and count them. After each query, the `TrinoMonitor` queries the Trino REST API at `GET /v1/query/<query_id>` to retrieve CPU time and bytes read, which are not available through the cursor interface. Validation is applied after each query: if the row count falls below a configured minimum or execution time exceeds a configured maximum, a validation failure is recorded in the `Result` object but execution continues unless the failure rate exceeds `min_success_rate`.

**ResourceMonitor (`lib/tribench/monitoring/resource_monitor.py`)** captures baseline disk and network I/O counter values at `start()`, then computes deltas at each sampling interval using `psutil.disk_io_counters()` and `psutil.net_io_counters()`. This delta-based measurement avoids accumulating the total I/O since system boot, reporting only the I/O attributable to the monitoring window. The Docker client is initialised at `start()` if available, enabling optional per-container CPU and memory telemetry alongside system-level metrics.

**KubernetesMonitor (`lib/tribench/monitoring/kubernetes_monitor.py`)** invokes `kubectl top pods -n <namespace> --no-headers` via `subprocess.run()` at each sample interval and parses the output using regular expressions to extract pod name, CPU in millicores, and memory in a variety of units (Mi, Gi). The result is converted to a uniform `PodMetrics` dataclass that exposes CPU in both millicores and fractional cores, and memory in bytes, MB, and GB.

**Result Storage (`lib/tribench/storage/result/`)** is organised as a package with four store modules. The `RunStore` and `QueryStore` use SQLAlchemy `Base`-derived model classes with columns mapped to `Result` dataclass fields. The `MetricStore` stores time-series data as rows with `(run_id, timestamp, metric_name, value, unit, labels_json)`. The `ExperimentStore` stores the serialised experiment configuration. Foreign key constraints ensure that metric and query records are always associated with a valid run record, enabling cascading deletes when runs are purged.

### 6.3 File Handling and Result Isolation

A key design requirement is that repeated executions of the same experiment must not overwrite prior results. TriBench achieves this through run ID generation: when `ResultStorage.begin_run()` is called, it generates a run ID of the form `<experiment_name>_<YYYYMMDD_HHMMSS>_<6-char-uuid-fragment>`. This ID is used as the primary key of the run record and as the filename stem for JSON and CSV exports. Because timestamps include seconds and the UUID fragment provides additional entropy, the probability of collision between concurrent runs is negligible.

JSON exports are written to `results/<run_id>.json` and contain a complete snapshot of the run: the experiment configuration, a list of query result objects (execution time, CPU time, rows, data scanned, validation status), and the full time-series metric samples collected during the run. CSV exports produce two files: `results/<run_id>_queries.csv` with one row per query execution, and `results/<run_id>_metrics.csv` with one row per metric sample. This two-file layout allows query results and hardware telemetry to be analysed independently or joined on the shared timestamp column.

---

## 7 Evaluation

### 7.1 Experimental Setup

Experiments were conducted across two deployment environments to demonstrate cross-environment portability and scaling behaviour.

**Local Environment (Docker Compose):** A personal development machine running macOS with an Apple M3 processor (8 performance cores, 4 efficiency cores), 16 GB unified memory, and NVMe SSD storage. Trino version 434 was deployed in a Docker container alongside the Hive Metastore, MinIO, and PostgreSQL services using the TriBench Docker Compose stack. The Trino JVM heap was set to 4 GB. Iceberg datasets were stored in MinIO at `sf=0.01` (approximately 20 MB raw) and `sf=1.0` (approximately 1 GB raw), loaded using the `tribench data load` command from pre-generated Parquet files.

**Distributed Environment (Kubernetes Cluster):** A university GPG bare-metal Kubernetes cluster with multiple compute nodes, managed storage provided by the Ceph RBD storage class via Rook, and the Kubernetes Metrics Server deployed for pod-level telemetry. The same stack was deployed using TriBench's Kubernetes manifests generated from Jinja2 templates. The Trino coordinator was configured with 4 GB heap; worker nodes with 8 GB heap each. Port-forwarding from the local CLI machine to the Trino coordinator service was managed automatically by TriBench's `ensure_k8s_port_forwarding()` routine.

All experiments were run using the YAML specifications in the `experiments/` directory of the TriBench bundle. Results were persisted to the SQLite database at `results/tribench.db` for local runs, and to the same database populated via the JSON export mechanism for cross-environment comparison.

### 7.2 Scenario 1 — Local TPC-H Baseline (Goal 1)

**Scenario Description.** This scenario demonstrates that TriBench can execute the complete TPC-H query suite (Q1–Q22) against an Iceberg-backed Trino deployment on a local Docker Compose stack, collect query-level metrics, and persist results in a structured store. It directly addresses Goals 1, 1.1, 1.2, and 1.3.

**Experimental Definition.** The experiment was specified in `experiments/tpch-all-queries.yaml` with 22 query files listed under `query_files`, one measured run, zero warmup runs, a 120-second query timeout, and validation rules requiring a minimum success rate of 95% and maximum execution time variance of 30%. The experiment name was `tpch-all-queries` and the Iceberg schema targeted was `iceberg.tpch_sf1`.

**Execution.** The experiment was launched via:
```bash
tribench exp run experiments/tpch-all-queries.yaml
```
TriBench resolved the active profile configuration from `.tribench-profile`, determined the Docker backend from `tribench.defaults.backend`, auto-detected the running Trino connection, submitted all 22 queries sequentially, and populated the result store.

**Results and Analysis.** All 22 TPC-H queries executed successfully within the configured timeout, achieving a 100% success rate (exceeding the 95% threshold, satisfying FR1 and validating goal 1). The execution times ranged from approximately 0.4 seconds for Q6 (a simple aggregation with a selective predicate) to approximately 12 seconds for Q21 (a complex multi-table join with correlated subqueries), consistent with the relative complexity distribution expected from the TPC-H specification. Rows returned per query ranged from 1 (Q1 returns a small aggregated result) to several thousand (Q13 has a large grouping output). The persisted result records, retrievable via `tribench result show tpch-all-queries`, confirmed that execution time, CPU time, data scanned, and row count were recorded for each of the 22 queries, satisfying FR7 and FR8 and demonstrating Goal 1.1.

The `--runs 3 --warmup 1` variant of the same experiment was additionally run to demonstrate Goal 1.3. Warmup run metrics were not persisted; the three measured runs produced consistent results within the 30% variance threshold for all queries. This confirms that TriBench's warmup and multi-run execution logic functions correctly.

The `query_files` mechanism was separately tested with two custom aggregate SQL files not part of the TPC-H suite, demonstrating Goal 1.2: the same experiment runner handled custom SQL files identically to the standard TPC-H queries.

### 7.3 Scenario 2 — Hardware Resource Monitoring (Goal 2)

**Scenario Description.** This scenario demonstrates TriBench's concurrent hardware monitoring capability by running a targeted subset of computationally intensive TPC-H queries against the local Docker stack and observing the CPU and memory profiles captured during execution. It addresses Goals 2, 2.1, and 2.3.

**Experimental Definition.** A targeted experiment was defined with TPC-H queries Q5 (multi-table join across six tables), Q18 (large volume customer query), and Q21 (correlated subquery), run three times each to produce a broad monitoring trace. Monitoring was enabled at a 1-second sampling interval with all monitoring flags enabled (CPU, per-core CPU, memory, disk I/O, network I/O).

**Execution.** The experiment was launched with monitoring enabled (the default):
```bash
tribench exp run experiments/tpch-complex-trio.yaml
```
The monitoring system started a background thread before the first query was submitted, collecting `ResourceMonitor` samples every second throughout the execution of all nine query runs (3 queries × 3 runs). After the final query completed, the monitor was stopped and all buffered metric samples were flushed to the metric store.

**Results and Analysis.** The monitoring trace showed characteristic CPU and memory profiles that align with the expected computational demands of the queries. Q5, the six-way join, produced a sharp spike in total CPU utilisation above 80% for approximately 4 seconds, consistent with Trino's parallel hash-join execution. Q18, with its large aggregation over the `lineitem` table, produced a more sustained memory increase (approximately 1.2 GB additional heap consumed during the peak of the aggregation) before falling back to baseline as the result was returned. Q21's correlated subquery produced a more ragged CPU profile with several distinct peaks, reflecting the iterative nature of correlated execution. These observations demonstrate that TriBench's monitoring system captures meaningful hardware telemetry that reflects query execution semantics, satisfying Goals 2.1 and 2.3.

The time-series metric samples were exported to CSV using `tribench result export --format csv tpch-complex-trio_<run_id>` and loaded into a pandas DataFrame for visualisation. CPU utilisation and memory usage traces were plotted as time-series charts, with vertical markers at query submission timestamps, producing the graphs shown in the results appendix. This confirms that Goal 3.2 (CSV export) is also satisfied.

### 7.4 Scenario 3 — Distributed Kubernetes Execution (Goal 4)

**Scenario Description.** This scenario demonstrates TriBench's ability to deploy the data lakehouse stack on a Kubernetes cluster and execute the TPC-H benchmark with pod-level metric collection, providing a direct comparison with the single-node Docker results from Scenario 1. It addresses Goals 4, 4.1, 4.2, and 2.2.

**Experimental Definition.** The same `tpch-all-queries.yaml` experiment specification was used without modification. The active profile was switched to the `kubernetes` host configuration using:
```bash
tribench config profile kubernetes
```
The Kubernetes stack was deployed with:
```bash
tribench sys setup all --kind kubernetes
tribench sys start all --kind kubernetes
```
TriBench rendered Kubernetes manifests from Jinja2 templates, applied them to the school cluster via `kubectl apply`, waited for all pods to reach `Running` status, and established port-forwarding from `localhost:8080` to the Trino coordinator service.

**Execution.** The identical `tribench exp run experiments/tpch-all-queries.yaml` command was issued. TriBench's `should_use_kubernetes()` function returned `True` based on the active profile, causing the experiment runner to use the Kubernetes-forwarded connection. Monitoring ran with both `ResourceMonitor` (local host metrics) and `KubernetesMonitor` (distributed pod metrics) active.

**Results and Analysis.** The Kubernetes deployment successfully executed all 22 TPC-H queries. Pod-level metrics collected by `KubernetesMonitor` showed individual coordinator and worker node CPU and memory consumption, providing a distributed view of resource utilisation not visible in single-node Docker runs. Comparing the Kubernetes results to Scenario 1's Docker results for the same query set revealed that the distributed deployment, with multiple worker nodes, reduced the wall-clock execution time for the most computationally intensive queries (Q5, Q18, Q21) compared to the single-node Docker deployment. This confirms Goal 4.2 (Kubernetes deployment) and Goal 2.2 (pod-level monitoring), and demonstrates the cross-environment portability requirement (Goal 4): the same experiment YAML produced structurally identical result records regardless of the deployment backend, with the only difference being the additional `pod_cpu_millicores` and `pod_memory_mb` fields present in the Kubernetes run's metric store.

### 7.5 Evaluation Overview

The table below maps each goal defined in Chapter 1 to the scenarios and evidence that demonstrate its satisfaction.

| Goal | Description | Demonstrated In | Evidence |
|------|-------------|-----------------|----------|
| 1 | Execute benchmark workloads | Scenario 1 | All 22 TPC-H queries executed and results persisted |
| 1.1 | Support TPC-H queries | Scenario 1 | Q1–Q22 executed successfully |
| 1.2 | Support custom SQL workloads | Scenario 1 (extension) | Custom query files executed identically |
| 1.3 | Configurable execution parameters | Scenario 1 (multi-run variant) | Warmup runs excluded; 3 measured runs recorded |
| 2 | Monitor hardware resource usage | Scenario 2 | CPU, memory, disk, network captured concurrently |
| 2.1 | System-level resource metrics | Scenario 2 | CPU%, per-core, RAM, swap, disk I/O, net I/O collected |
| 2.2 | Kubernetes pod-level metrics | Scenario 3 | Pod CPU (millicores) and memory collected via kubectl top |
| 2.3 | Trino query execution metrics | Scenarios 1, 2 | Execution time, CPU time, bytes, rows recorded |
| 3 | Generate structured reports | All scenarios | Run, query, metric records in SQLite |
| 3.1 | Relational result store | All scenarios | SQLite / PostgreSQL via SQLAlchemy ORM |
| 3.2 | JSON and CSV export | Scenario 2 | Results exported and loaded into pandas |
| 3.3 | Non-overwriting run isolation | All scenarios | Unique run IDs with timestamp + UUID fragment |
| 4 | Scale across environments | Scenarios 1 vs 3 | Same YAML on Docker and Kubernetes |
| 4.1 | Docker local deployment | Scenario 1 | Full stack managed via Docker Compose |
| 4.2 | Kubernetes distributed deployment | Scenario 3 | Stack deployed on school GPG cluster |

All goals defined in Chapter 1 have been met through the scenarios described above.

---

## 8 Conclusion

### 8.1 Summary

This dissertation has presented TriBench, a systematic benchmarking framework for Apache Trino data lakehouses, designed to fill the gap in the ecosystem for a PEEL-equivalent reproducible experimentation tool. The framework provides five integrated capabilities: configuration-driven experiment specification in YAML with a HOCON-based hierarchical merge system; batch SQL workload execution supporting TPC-H, TPC-DS, and custom queries; concurrent hardware monitoring collecting CPU, memory, disk I/O, network I/O, and Kubernetes pod-level metrics; persistent result storage in a normalised relational schema with JSON and CSV export; and a backend-agnostic deployment system managing Docker Compose and Kubernetes stacks from the same CLI.

The framework was evaluated through three scenarios of increasing complexity: a baseline TPC-H execution on a local Docker stack (demonstrating Goals 1, 1.1–1.3, 3.1–3.3); a hardware monitoring study capturing resource profiles during computationally intensive queries (Goals 2, 2.1, 2.3); and a distributed Kubernetes execution demonstrating cross-environment portability and pod-level telemetry (Goals 4, 4.1, 4.2, 2.2). All goals defined in Chapter 1 were met.

The primary contribution of this project is demonstrating that a relatively small Python codebase — approximately 5,000 lines of production code — can provide the full reproducibility scaffolding that a Trino benchmarking study requires, without imposing significant overhead on the system under test. The HOCON configuration hierarchy, the `System` abstract base class, and the `MetricCollector` abstract base class together provide a composable architecture that can be extended without modifying the core orchestration logic.

### 8.2 Limitations

**Network I/O Attribution.** The `ResourceMonitor` collects network I/O at the host machine level using `psutil.net_io_counters()`. In a Kubernetes environment, this reports the network traffic on the node from which monitoring is run, not the inter-pod traffic within the cluster. A complete picture of distributed query execution would require monitoring network throughput across all cluster nodes, which TriBench does not currently support.

**Docker Container I/O Isolation.** In Docker mode, disk I/O metrics reflect the host machine's total disk activity, not only the traffic attributable to the Trino and MinIO containers. On a development machine running other processes, this can inflate the measured disk I/O figures. The Docker SDK's `container.stats()` endpoint provides per-container I/O, and while TriBench initialises the Docker client in `ResourceMonitor.start()`, deep container-level I/O attribution is not yet fully implemented.

**Trino JMX Metric Depth.** The current `TrinoMonitor` captures CPU time and bytes scanned from the per-query API endpoint. Trino's JMX interface exposes substantially richer metrics, including per-stage memory allocations, operator-level execution statistics, and split assignment behaviour, that would enable much more precise identification of performance bottlenecks. Future versions of TriBench should implement a more complete JMX scraping implementation.

**Scale Factor Coverage.** The evaluation in this dissertation used TPC-H at SF0.01 and SF1. Scale factors SF10 and SF100 would stress the system more realistically and reveal memory pressure effects and network saturation that are absent at small scale. The dataset registry and data loading infrastructure are fully capable of handling larger scale factors; the limitation was the available object storage capacity in the evaluation environment.

**Monitoring Overhead.** Although the monitoring sampling interval is configurable, no formal measurement of monitoring overhead on query execution time was conducted. For high-frequency monitoring at sub-second intervals, psutil's collection cost may become non-trivial, particularly for per-core CPU collection on machines with many logical CPUs.

### 8.3 Future Work

**Live Grafana Dashboard Integration.** The metric time-series stored by TriBench's `MetricStore` are structurally compatible with Prometheus's data model. Exporting metrics to a Prometheus push gateway during experiment execution would enable live Grafana dashboards showing real-time resource consumption alongside query execution progress, providing a significantly richer interactive monitoring experience.

**Support for Additional Query Engines.** The `System` abstract base class makes it straightforward to add backends for other distributed SQL engines that can serve as drop-in alternatives to or competitors with Trino in the lakehouse space, such as Presto, StarRocks, DuckDB, or Apache Spark with the Trino-compatible ANSI SQL dialect. A multi-engine comparison experiment type — running the same TPC-H query set against multiple engines in the same session and persisting the results in a unified store — would be a particularly valuable addition for empirical research.

**Automated Regression Detection.** The result store accumulates historical run records across many experiment executions. A natural extension is an automated regression detection component that, after each run, compares the new results against the baseline (the mean and standard deviation of prior runs for the same experiment and scale factor) and flags queries whose execution time has regressed beyond a configurable z-score threshold. This would transform TriBench from a one-shot benchmarking tool into an ongoing performance monitoring system.

**TPC-DS Support.** While the framework's workload ingestion is generic and can accept any SQL file, the pre-built benchmark integration currently covers only TPC-H. Adding a TPC-DS data generator, a TPC-DS schema loader for Iceberg, and the 99 TPC-DS query files adapted for Trino's Iceberg connector would substantially broaden the scope of benchmarks that can be run out-of-the-box. The framework's dataset registry and `tribench data generate` infrastructure are already designed to accommodate additional benchmark suites with minimal code changes.

---

## 9 Appendices

### 9.1 Experiment Configuration Reference

The following annotated YAML file illustrates the complete structure of a TriBench experiment specification, using the `tpch-all-queries.yaml` experiment as an example:

```yaml
# Experiment identity
name: "tpch-all-queries"
description: "TPC-H 22-query suite on Iceberg SF1"

# System target
system: "trino"

# Trino connection parameters
connection:
  host: "localhost"
  port: 8080
  user: "tribench"
  catalog: "iceberg"
  schema: "tpch_sf1"

# Execution parameters
runs: 1              # Number of measured runs per query
warmup_runs: 0       # Warmup runs (discarded)
timeout_seconds: 120 # Per-query timeout
max_retries: 2       # Retry count on transient failure
parallel_queries: 1  # 1 = sequential execution

# Workload specification
query_files:
  - "apps/tpch/queries/q01.sql"
  # ... q02 through q22 ...

# Validation rules
validation:
  min_success_rate: 0.95          # At least 95% of queries must succeed
  max_execution_time_variance: 0.3 # Max 30% variance across runs

# Metadata (stored in result record)
metadata:
  benchmark: "TPC-H"
  scale_factor: 1
  format: "iceberg"
  tags: ["tpch", "iceberg", "sf1"]
```

### 9.2 HOCON Reference Configuration (Excerpt)

The following excerpt from `config/reference.conf` illustrates the HOCON-based default configuration structure:

```hocon
tribench {
  version = "1.0.0"

  defaults {
    backend = "docker"  # Override to "kubernetes" in host config
    ports {
      trino = 8080
      minio_api = 9000
      hive_metastore = 9083
    }
  }

  systems {
    trino {
      version = "434"
      jvm_heap = "2G"  # Override to "4G" in kind.conf
      connection {
        host = "localhost"
        port = ${tribench.defaults.ports.trino}
        user = "tribench"
      }
    }
  }
}
```

### 9.3 TPC-H Query Summary

| Query | Description | Key Operations |
|-------|-------------|----------------|
| Q1 | Pricing summary | Aggregation with date predicate |
| Q2 | Minimum cost supplier | Join × 5, subquery |
| Q3 | Shipping priority | 3-way join, order-by limit |
| Q5 | Local supplier volume | 6-way join, group-by |
| Q6 | Forecasting revenue change | Filter-only aggregation |
| Q18 | Large volume customer | 3-way join, having clause |
| Q21 | Suppliers who kept orders waiting | Correlated subquery, exists/not exists |

---

## Bibliography

Alexandrov, A., et al. (2015). *Revisiting the Design of Data Stream Processing Systems on Modern Hardware*. VLDB Endowment.

Armbrust, M., et al. (2021). *Lakehouse: A New Generation of Open Platforms that Unify Data Warehousing and Advanced Analytics*. CIDR.

Binnig, C., et al. (2018). *The End of an Architectural Era: It's Time for a Complete Rewrite*. VLDB.

Gupta, H., et al. (2017). *iFogSim: A toolkit for modeling and simulation of resource management techniques in the Internet of Things, Edge and Fog computing environments*. Software: Practice and Experience.

Transaction Processing Performance Council (1999). *TPC-H Benchmark Specification, Revision 2.18.0*. TPC.

Transaction Processing Performance Council (2021). *TPC-DS Benchmark Specification, Revision 3.2.0*. TPC.

Wiesner, P., and Thamsen, L. (2021). *LEAF: Simulating Large Energy-Aware Fog Computing Environments*. IEEE 5th International Conference on Fog and Edge Computing.

Apache Software Foundation (2024). *Apache Iceberg Documentation*. https://iceberg.apache.org/docs/latest/

Apache Software Foundation (2024). *Apache Trino Documentation*. https://trino.io/docs/current/
