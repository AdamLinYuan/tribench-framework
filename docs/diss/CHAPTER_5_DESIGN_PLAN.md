# Chapter 5: Design - Detailed Plan

## Overview
Chapter 5 presents the architecture of TriBench, mapping requirements from Chapter 4 to architectural decisions. The chapter follows a top-down approach: starting with high-level architecture, then diving into each layer and cross-cutting concern.

**Length target**: 15-20 pages  
**Figures needed**: 8 diagrams (outlined below)  
**Code listings**: 2-3 short config/code excerpts

---

## Opening Paragraph (1 paragraph, ~100 words)

**Content**: Introduce how design satisfies requirements.

**Key points**:
- Five-layer architecture (CLI → Configuration → Orchestration → Systems → Data Lakehouse)
- Two cross-cutting concerns (Monitoring and Result Storage)
- Design principles: modularity, portability, reproducibility
- Reference back to requirements (M1-M21, S1-S4, C1)

**Example opening**:
> "This chapter presents TriBench's architecture, translating the requirements from Chapter 4 into concrete design decisions. The framework follows a five-layer architecture: CLI, Configuration, Orchestration, Systems, and Data Lakehouse. Two cross-cutting concerns—monitoring and result storage—integrate across multiple layers. The design prioritizes modularity (S3), portability (M20), and reproducibility (M19) through bundle abstraction (M15-M18), layered configuration (M14), and database-backed storage (M8-M10)."

---

## Section 5.1: Architectural Overview (2-3 pages)

### 5.1.1: Five-Layer Architecture

**Diagram needed**: **Figure 5.1 - Five-layer architecture diagram**

**Content**:
1. **Layer enumeration** (top to bottom):
   - **CLI Layer**: Single entry point via `tribench` command; seven command groups
   - **Configuration Layer**: Five-level HOCON hierarchy with variable substitution
   - **Orchestration Layer**: ExperimentConfig, Runner, Suite abstraction
   - **Systems Layer**: Docker backend | Kubernetes backend (both implement System ABC)
   - **Data Lakehouse Layer**: Trino, Iceberg, MinIO, Hive Metastore, PostgreSQL

2. **Control flow**: User command descends through layers (solid arrows downward)
   - Example: `tribench exp run tpch-all-queries.yaml`
   - CLI parses → loads config → builds ExperimentConfig → orchestrates → starts systems → executes queries

3. **Data flow**: Results ascend (dashed arrows upward)
   - Query stats + telemetry → monitoring buffer → result storage → database
   - Export commands pull from storage → JSON/CSV files

4. **Cross-cutting concerns**:
   - **Monitoring subsystem**: Integrates into layers 3-5 (orchestration, systems, lakehouse)
   - **Result storage**: Receives data from layers 3-4 (orchestration, systems)

**Requirements mapping**:
- M1: Declarative specification (Orchestration layer)
- M6-M7: Monitoring (cross-cutting)
- M8-M10: Result storage (cross-cutting)
- M11-M14: Systems layer
- M15-M18: Bundle abstraction (Configuration layer)

### 5.1.2: Design Principles

**Content**: Brief subsection explaining key principles
1. **Separation of concerns**: Each layer has single responsibility
2. **Abstraction**: System ABC allows new backends (C1)
3. **Configuration-driven**: Behavior controlled by HOCON, not code
4. **Database-backed**: Queryable historical results (M8)

**Length**: 1 page

---

## Section 5.2: CLI Layer (1.5 pages)

### Content

1. **Entry point**: Single `tribench` command (Click 8)
2. **Seven command groups**:
   - `tribench bundle`: Create, activate, archive bundles
   - `tribench sys`: System lifecycle (setup, start, stop, teardown, status, logs)
   - `tribench data`: Dataset registration and loading
   - `tribench exp`: Experiment execution
   - `tribench result`: Export, query historical results
   - `tribench config`: Show, validate configuration
   - `tribench suite`: Execute experiment suites

3. **TriBenchContext**: Shared context object passed via Click's context
   - Bundle root path
   - Verbose flag
   - Dry-run mode
   - Active configuration

4. **Help text**: Auto-generated via Click decorators

**Code listing**: Example CLI invocation
```bash
# Example showing CLI command structure
tribench bundle create my-study
tribench config profile set trino-4workers
tribench exp run experiments/tpch-all-queries.yaml
tribench result export tpch-run --format csv
```

**Requirements mapping**: M1 (declarative), M15-M18 (bundle commands)

---

## Section 5.3: Bundle Abstraction (2 pages)

### 5.3.1: Bundle Structure

**Diagram needed**: **Figure 5.2 - Bundle directory structure**

```
my-tpch-study/
├── bundle.yaml                   # Manifest
├── config/
│   ├── application.conf          # Bundle-level config
│   └── hosts/
│       ├── docker-dev.conf       # Docker profile
│       └── trino-4workers.conf   # K8s 4-worker profile
├── experiments/
│   ├── tpch-all-queries.yaml
│   └── tpch-subset.yaml
├── datasets/
│   ├── registry.yaml             # Dataset catalog
│   └── custom-data/
│       └── my_table/
├── apps/
│   └── tpch/
│       └── queries/              # Query files
├── log/                          # Execution logs
└── results/
    └── tribench.db               # SQLite results
```

### 5.3.2: Bundle Lifecycle

**Content**:
1. **Creation**: `tribench bundle create <name>`
   - Scaffolds directory structure
   - Generates template `bundle.yaml`
   - Copies reference configs

2. **Activation**: `tribench bundle set <path>`
   - Stores active bundle path in `~/.tribench-bundle`
   - All commands operate on active bundle

3. **Auto-detection**: Walks upward from CWD searching for `bundle.yaml`

4. **Archiving**: `tribench bundle archive <name>`
   - Creates `.tar.gz` with all subdirectories
   - Includes results database, logs, configs
   - Shareable, long-term storage (M18)

**Code listing**: `bundle.yaml` manifest
```yaml
name: my-tpch-study
version: 1.0.0
description: TPC-H scalability study
created: 2026-03-01
framework_version: 0.5.0
```

**Requirements mapping**: M15-M18 (bundle abstraction), M19 (reproducibility)

---

## Section 5.4: Configuration Layer (3-4 pages)

### 5.4.1: Five-Level HOCON Hierarchy

**Diagram needed**: **Figure 5.3 - Five-level HOCON configuration hierarchy**

**Waterfall diagram** showing merge cascade:
```
Layer 1: reference.conf (framework defaults)
   ↓ (overridden by)
Layer 2: Named profile (config/hosts/trino-4workers.conf)
   ↓ (overridden by)
Layer 3: application.conf (bundle-level)
   ↓ (overridden by)
Layer 4: Experiment YAML (tpch-all-queries.yaml)
   ↓ (overridden by)
Layer 5: CLI arguments (--config-override trino.workers=8)

Example key: trino.workers
  reference.conf:         trino.workers = 1
  trino-4workers.conf:    trino.workers = 4
  application.conf:       (not set)
  experiment YAML:        (not set)
  CLI override:           trino.workers = 8
  → Final value: 8
```

**Rationale**: Same bundle runs on different hardware without editing experiments (M13, M14, M19)

### 5.4.2: Variable Substitution

**Content**: HOCON variables enable profile reuse

**Code listing**: `reference.conf` excerpt
```hocon
tribench {
  systems {
    trino {
      workers = 1
      coordinator_memory = "4G"
      worker_memory = "4G"
      backend = "docker"  # "docker" or "kubernetes"
    }
  }
}
```

**Code listing**: `config/hosts/trino-4workers.conf` profile
```hocon
tribench {
  systems {
    trino {
      workers = 4
      worker_memory = "8G"
      backend = "kubernetes"
    }
  }
}
```

**Explanation**: Engineer switches profiles via `tribench config profile set trino-4workers`; experiments run unmodified.

### 5.4.3: Profile Table

**Table**: Representative profiles shipped with framework

| Profile              | Backend    | Workers | Coordinator Mem | Worker Mem | Use Case               |
|----------------------|------------|---------|-----------------|------------|------------------------|
| `docker-dev`         | Docker     | 1       | 4G              | 4G         | Local development      |
| `trino-1worker`      | Kubernetes | 1       | 4G              | 4G         | Baseline K8s           |
| `trino-4workers`     | Kubernetes | 4       | 4G              | 8G         | Scaling study          |
| `trino-8workers`     | Kubernetes | 8       | 4G              | 8G         | Large-scale benchmark  |
| `gcs-remote`         | Kubernetes | 4       | 4G              | 8G         | Cloud storage (GCS)    |

**Requirements mapping**: M13 (cross-backend portability), M14 (named profiles), M19 (reproducibility)

---

## Section 5.5: Orchestration Layer (2 pages)

### Content

1. **ExperimentConfig dataclass** (`lib/tribench/experiments/config.py`)
   - Loaded via `ExperimentConfig.from_yaml()`
   - Implements three-tier merge: reference.conf ← bundle config ← experiment YAML

2. **Runner** (`lib/tribench/experiments/runner.py`)
   - Submits SQL queries to Trino via `trino` Python client
   - Drains cursor with `cursor.fetchall()` to capture row count
   - Fetches per-query stats from `GET /v1/query/{queryId}` REST endpoint
   - Validates success rate threshold (M5)
   - Discards warmup runs; saves measured runs to storage

3. **Suite abstraction** (S1)
   - Groups experiments with shared lifecycle
   - Suite defaults ← experiment YAML ← CLI overrides
   - Automatic system start/stop around suite execution

**Workflow**:
1. Load experiment config (3-tier merge)
2. Start systems (Docker or K8s based on `backend` key)
3. Start monitoring session
4. Execute warmup runs (discard results)
5. Execute measured runs (save to storage)
6. Stop monitoring (flush metrics to storage)
7. Stop systems
8. Generate run ID: `<name>_<YYYYMMDD_HHMMSS>_<6-hex-UUID>` (M10)

**Requirements mapping**: M1 (declarative), M4 (unified query spec), M5 (execution control), M10 (unique run IDs), S1 (suites)

---

## Section 5.6: Monitoring System (3 pages)

### 5.6.1: Architecture

**Diagram needed**: **Figure 5.4 - Monitoring subsystem architecture**

**Component diagram**:
- **MonitoringSession** (coordinator)
- **Three MetricCollector threads** (running concurrently):
  1. `SystemResourceCollector` (psutil → CPU/RAM/Disk I/O/Network I/O samples)
  2. `KubernetesPodCollector` (kubectl top pods → per-pod CPU/memory)
  3. `TrinoQueryCollector` (REST `/v1/query/{id}` → query CPU time, bytes scanned)
- **Shared MonitoringConfig**: `sampling_interval`, enabled collector flags
- **Shared metric buffer**: Thread-safe queue (list + lock)
- **threading.Event `stop_flag`**: Coordinated shutdown
- **ResultStorage**: Receives flush on stop

### 5.6.2: MetricCollector ABC

**Content**:
- Abstract base class: `start()`, `stop()`, `collect()`
- Each collector runs in background thread
- Collects metrics at `sampling_interval` (default: 1 second)
- Buffers metrics; flushed to storage on `stop()`

### 5.6.3: SystemResourceCollector

**Implementation** (`lib/tribench/monitoring/system_resources.py`):
- Uses `psutil` library for host-level telemetry
- **Metrics**:
  - CPU utilization (percent per core, aggregate)
  - Memory (used, available, percent)
  - Disk I/O (read/write bytes/sec) — delta from baseline
  - Network I/O (sent/received bytes/sec) — delta from baseline
- **Baseline correction**: Captures initial I/O counters; reports deltas to exclude background activity

### 5.6.4: KubernetesPodCollector

**Implementation** (`lib/tribench/monitoring/kubernetes_pods.py`):
- Invokes `kubectl top pods -n tribench` at each interval
- Parses output into `PodMetrics` dataclass
- Normalizes CPU (millicores) and memory (bytes)
- Stores per-pod metrics: `trino-coordinator-0`, `trino-worker-0`, `trino-worker-1`, etc.
- Enabled only when `backend=kubernetes`

### 5.6.5: TrinoQueryCollector

**Implementation** (`lib/tribench/monitoring/trino_queries.py`):
- Not interval-based; triggered after each query execution
- Fetches from `GET /v1/query/{queryId}` REST endpoint
- **Metrics**:
  - Wall-clock time (milliseconds)
  - CPU time (milliseconds)
  - Bytes scanned
  - Rows returned
- Stored as `QueryExecution` record (linked to `ExperimentRun`)

**Requirements mapping**: M6 (host telemetry), M7 (per-query stats), S2 (K8s pod metrics), S4 (low overhead)

---

## Section 5.7: Systems Layer (4-5 pages)

### 5.7.1: System Abstract Base Class

**Content**:
- Located: `lib/tribench/core/system.py`
- Four lifecycle methods (all abstract):
  - `setup()`: Download binaries, create directories, generate configs
  - `start()`: Launch services, wait for readiness
  - `stop()`: Graceful shutdown
  - `teardown()`: Remove containers, volumes, optionally files
- One query method:
  - `status()`: Returns `Dict[str, Any]` with running state, health, ports

**Diagram needed**: **Figure 5.5 - System lifecycle state machine**

```
[Not Configured] --setup()--> [Configured]
[Configured] --start()--> [Running]
[Running] --stop()--> [Stopped]
[Stopped] --teardown()--> [Not Configured]
[Running] --teardown()--> [Not Configured]  (emergency cleanup)
```

**Annotations**:
- `setup()`: Render templates, create dirs, pull images
- `start()`: docker-compose up / kubectl apply, poll readiness
- `stop()`: docker-compose down / kubectl delete
- `teardown()`: Remove files, cleanup volumes

### 5.7.2: Docker Backend

**Implementation**: `TrinoSystem`, `PostgreSQLSystem`, `MinIOSystem`, `HiveMetastoreSystem`

**Pipeline**:
1. **Setup phase**:
   - Download Trino binary (JAR) to `~/.tribench/systems/trino/<version>/`
   - Generate `docker-compose.yml` from Jinja2 template
   - Generate Trino config files: `config.properties`, `jvm.config`, `catalog/iceberg.properties`
   - Pull Docker images: `trinodb/trino:latest`, `postgres:15`, `minio/minio:latest`, `apache/hive:3.1.3`

2. **Start phase**:
   - `docker-compose up -d` (detached mode)
   - Wait for health checks: Trino `/v1/info`, Postgres `pg_isready`, MinIO `/minio/health/live`
   - Timeout: 120 seconds (configurable via `Defaults.Timeouts.TRINO`)

3. **Stop phase**:
   - `docker-compose down` (graceful)
   - Force mode: `docker-compose down -t 0` (immediate)

4. **Teardown phase**:
   - `docker-compose down -v` (remove volumes)
   - Delete `~/.tribench/systems/trino/<version>/` if `keep_data=False`

**Diagram needed**: **Figure 5.6 - Docker backend deployment**

```
tribench-network (bridge)
  ├── trino-coordinator (port 8080)
  ├── hive-metastore (port 9083)
  ├── minio (ports 9000, 9001)
  └── postgres (port 5432)

Volumes:
  - minio-data
  - postgres-data

Connections:
  - Trino → Hive Metastore (Iceberg catalog)
  - Hive Metastore → Postgres (catalog DB)
  - Trino → MinIO (S3-compatible storage)
```

**Rationale for component choices**:
- **Trino**: Primary query engine under test
- **Iceberg**: Modern table format with schema evolution, time travel
- **MinIO**: S3-compatible object storage; reproducible local deployment (vs. cloud dependencies)
- **Hive Metastore**: Iceberg catalog implementation; widely adopted
- **PostgreSQL**: Metastore backend database; ACID guarantees
- **Docker Compose**: Single-machine orchestration; developer-friendly

### 5.7.3: Kubernetes Backend

**Implementation**: `KubernetesSystem` (`lib/tribench/systems/kubernetes_system.py`)

**Pipeline**:
1. **Setup phase**:
   - Render Kubernetes manifests from Jinja2 templates:
     - `trino-coordinator-statefulset.yaml`
     - `trino-worker-statefulset.yaml` (replicas controlled by `trino.workers`)
     - `hive-metastore-statefulset.yaml`
     - `minio-statefulset.yaml`
     - `postgres-statefulset.yaml`
     - Service definitions for each component
     - PersistentVolumeClaims (MinIO, Postgres)
   - Create namespace: `kubectl create namespace tribench`

2. **Start phase**:
   - `kubectl apply -f manifests/` (idempotent)
   - Poll pod readiness: `kubectl get pods -n tribench`
   - Wait for all pods: Running + Ready
   - Timeout: 300 seconds (K8s slower than Docker)
   - **Automatic port-forwarding**: `kubectl port-forward svc/trino-svc 8080:8080 -n tribench &`
     - Enables CLI to connect to Trino coordinator at `localhost:8080`

3. **Stop phase**:
   - Kill port-forward process
   - `kubectl delete -f manifests/`
   - Keep namespace (optional)

4. **Teardown phase**:
   - `kubectl delete namespace tribench --force --grace-period=0`
   - Delete rendered manifest files if `keep_data=False`

**Diagram needed**: **Figure 5.7 - Kubernetes backend deployment**

```
Namespace: tribench

Pods:
  - trino-coordinator-0
  - trino-worker-0
  - trino-worker-1
  - ...
  - trino-worker-N  (N = trino.workers)
  - hive-metastore-0
  - minio-0
  - postgres-0

Services:
  - trino-svc (ClusterIP, port 8080)
  - hive-metastore-svc (ClusterIP, port 9083)
  - minio-svc (ClusterIP, ports 9000, 9001)
  - postgres-svc (ClusterIP, port 5432)

PVCs:
  - minio-pvc (10Gi)
  - postgres-pvc (5Gi)

Port-forward:
  localhost:8080 → trino-svc:8080

TriBench CLI (external) → port-forward → Trino coordinator
```

**Scaling capability**: Change `trino.workers` in profile → re-apply manifest → K8s schedules new worker pods

**Requirements mapping**: M11 (Docker lifecycle), M12 (K8s lifecycle), M13 (cross-backend portability), M14 (profiles switch backends)

---

## Section 5.8: Result Storage (2 pages)

### 5.8.1: Database Schema

**Diagram needed**: **Figure 5.8 - Result storage schema (ER diagram)**

**Entities**:
1. **Experiment** (table: `experiments`)
   - `id` (PK, auto-increment)
   - `name` (string, unique)
   - `config_snapshot` (JSON blob, stores full ExperimentConfig)

2. **ExperimentRun** (table: `experiment_runs`)
   - `id` (PK, auto-increment)
   - `experiment_id` (FK → experiments.id, CASCADE DELETE)
   - `run_id` (string, unique, format: `<name>_<YYYYMMDD_HHMMSS>_<UUID>`)
   - `timestamp` (datetime)
   - `status` (string: "SUCCESS", "PARTIAL", "FAILED")
   - `profile_name` (string, e.g., "trino-4workers")

3. **QueryExecution** (table: `query_executions`)
   - `id` (PK, auto-increment)
   - `run_id` (FK → experiment_runs.id, CASCADE DELETE)
   - `query_name` (string)
   - `query_index` (int, order within run)
   - `wall_time_ms` (int)
   - `cpu_time_ms` (int)
   - `bytes_scanned` (bigint)
   - `rows_returned` (bigint)
   - `status` (string: "SUCCESS", "TIMEOUT", "FAILED")

4. **MonitoringMetric** (table: `monitoring_metrics`)
   - `id` (PK, auto-increment)
   - `run_id` (FK → experiment_runs.id, CASCADE DELETE)
   - `timestamp` (datetime, high precision)
   - `metric_type` (string: "cpu_percent", "memory_used", "disk_read_bps", "pod_cpu_millicores", etc.)
   - `value` (float)
   - `unit` (string: "percent", "bytes", "millicores", etc.)
   - `source` (string: "system", "kubernetes", "trino")
   - `pod_name` (nullable string, for K8s pod-level metrics)

**Relationships**:
- Experiment 1-to-many ExperimentRun
- ExperimentRun 1-to-many QueryExecution
- ExperimentRun 1-to-many MonitoringMetric
- **Cascade deletes**: Deleting ExperimentRun removes all associated queries and metrics

### 5.8.2: SQLAlchemy ORM

**Content**:
- ORM models: `lib/tribench/storage/models.py`
- Database-agnostic: SQLite (default, `results/tribench.db`) or PostgreSQL (production)
- Session management: Context manager ensures commits/rollbacks
- Foreign key constraints enforce referential integrity

### 5.8.3: Export Formats

**JSON export** (`tribench result export <run_id> --format json`):
- Single file: `<run_id>.json`
- Contains:
  - `config`: Full ExperimentConfig snapshot
  - `queries`: Array of QueryExecution records
  - `metrics`: Array of MonitoringMetric records
- Use case: Machine-readable, complete snapshot for archiving (M9)

**CSV export** (`tribench result export <run_id> --format csv`):
- Two files:
  - `<run_id>_queries.csv`: One row per query execution
  - `<run_id>_metrics.csv`: One row per metric sample
- Use case: Import into pandas, R, Excel for statistical analysis (M9)

**Requirements mapping**: M8 (relational schema), M9 (export formats), M10 (unique run IDs)

---

## Section 5.9: Summary (1 paragraph, ~100 words)

**Content**: Recap architectural decisions and forward reference to implementation.

**Example**:
> "This chapter presented TriBench's five-layer architecture, demonstrating how requirements from Chapter 4 translate into design decisions. The CLI layer provides a unified entry point via seven command groups. The configuration layer implements a five-level HOCON hierarchy enabling cross-environment portability via named profiles. The orchestration layer coordinates experiment execution, invoking the systems layer to manage Docker or Kubernetes deployments. Two cross-cutting concerns—monitoring and result storage—capture concurrent telemetry and persist results in a queryable relational schema. Chapter 6 describes the implementation of this architecture in Python 3.9."

---

## Summary of Figures

1. **Figure 5.1**: Five-layer architecture diagram (control flow, data flow, cross-cutting concerns)
2. **Figure 5.2**: Bundle directory structure (tree diagram)
3. **Figure 5.3**: Five-level HOCON configuration hierarchy (waterfall/cascade diagram)
4. **Figure 5.4**: Monitoring subsystem architecture (component diagram)
5. **Figure 5.5**: System lifecycle state machine (state diagram)
6. **Figure 5.6**: Docker backend deployment (network diagram)
7. **Figure 5.7**: Kubernetes backend deployment (cluster diagram)
8. **Figure 5.8**: Result storage schema (ER diagram)

---

## Code Listings

1. **Listing 5.1**: CLI command examples (bash)
2. **Listing 5.2**: `bundle.yaml` manifest (YAML)
3. **Listing 5.3**: `reference.conf` excerpt (HOCON)
4. **Listing 5.4**: `trino-4workers.conf` profile (HOCON)

---

## Writing Tips

1. **Concise, direct language**: Follow the condensed style from Requirements chapter
2. **Passive voice avoidance**: "The CLI layer provides" not "The CLI layer is provided"
3. **Requirements traceability**: Explicitly cite requirement IDs (M1, M6, etc.) when explaining design decisions
4. **Forward references**: "Chapter 6 describes implementation details"
5. **Backward references**: "Requirement M13 from Chapter 4 mandates cross-backend portability"
6. **Diagram integration**: "Figure 5.1 illustrates the five-layer architecture"
7. **Rationale**: Explain *why* each design choice was made (reproducibility, portability, extensibility)

---

## Estimated Page Count Breakdown

| Section                       | Pages |
|-------------------------------|-------|
| Opening                       | 0.25  |
| 5.1 Architectural Overview    | 2.5   |
| 5.2 CLI Layer                 | 1.5   |
| 5.3 Bundle Abstraction        | 2.0   |
| 5.4 Configuration Layer       | 3.5   |
| 5.5 Orchestration Layer       | 2.0   |
| 5.6 Monitoring System         | 3.0   |
| 5.7 Systems Layer             | 4.5   |
| 5.8 Result Storage            | 2.0   |
| 5.9 Summary                   | 0.25  |
| **Total**                     | **21.5** |

---

## Next Steps

1. **Write Section 5.1** (Architectural Overview) with Figure 5.1
2. **Create all 8 diagrams** using draw.io, Lucidchart, or TikZ
3. **Write sections 5.2-5.8** following this plan
4. **Add code listings** as specified
5. **Proofread for conciseness**: Remove filler words, passive voice
6. **Cross-check requirements**: Ensure all M1-M21, S1-S4, C1 are mapped to design elements
7. **Forward to Chapter 6**: Implementation chapter should reference these design decisions
