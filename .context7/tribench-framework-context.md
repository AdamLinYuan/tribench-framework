# TriBench Framework - Complete Codebase Context

**Last Updated**: November 22, 2025  
**Version**: 1.0.0-dev  
**Author**: Adam Yuan  
**Institution**: University of Glasgow  
**Project Type**: MSc Computer Science Dissertation

---

## Executive Summary

TriBench is a PEEL-inspired benchmarking framework for Apache Trino, designed to systematically evaluate SQL query performance on distributed data lakehouses. The framework provides structured experiment definition, automated system lifecycle management, resource monitoring, and result analysis capabilities.

**Primary Research Question (Updated)**: How can we design and implement a systematic, reproducible benchmarking framework for Apache Trino that supports executing batch workloads, monitoring resource usage, and generating structured performance reports across single-node and distributed cluster environments?

**Current Status**: Phase 0-3.2 complete + Suite System Enhancements (Weeks 1-26)
- ✅ **Phase 0-1**: Foundation, MVP framework, CLI, testing infrastructure (Weeks 1-14)
- ✅ **Phase 2.1**: Iceberg integration (PostgreSQL, Hive Metastore, MinIO) (Week 15)
- ✅ **Phase 2.2**: TPC-H benchmark suite (all 22 queries), experiment suites, validation (Week 16)
- ✅ **Phase 3.1**: Resource monitoring (system, Trino metrics, alerts) (Weeks 18-20)
- ✅ **Phase 3.2**: Database result storage (SQLite, PostgreSQL, rich CLI) (Weeks 21-25)
- ✅ **Suite System**: Smart lifecycle management, catalog detection, improved health checks (Week 26)
- ✅ **Templates**: Complete reference templates for experiments and suites (Week 26)
- 🔄 **Phase 3.3**: Analysis Engine - Weeks 27-28 (upcoming)
- 🔄 **Phase 4**: Kubernetes Cluster Deployment - Weeks 29-38 (planned)

**Key Achievements**: 
- Production-ready monitoring and database storage infrastructure
- Intelligent suite execution with catalog-based dependency detection
- Enhanced three-layer health verification for robust system readiness
- Comprehensive template library (355-450 line reference documents)
- Smart lifecycle management with status-based decision tree
- Kubernetes deployment documentation for distributed clusters
- Framework provides comprehensive performance tracking, structured result storage, and analysis capabilities for rigorous benchmarking studies

---

## Project Architecture

### High-Level Design

TriBench follows a **bundle-based architecture** inspired by the PEEL framework:

```
tribench-framework/
├── bin/                    # Command-line interface entry point
│   └── tribench.sh        # Shell dispatcher
├── lib/tribench/          # Core framework implementation
│   ├── core/              # Abstract base classes
│   ├── cli/               # Command-line interface
│   ├── systems/           # System implementations (Trino, PostgreSQL)
│   ├── experiments/       # Experiment execution engine
│   ├── data/              # Dataset management
│   ├── monitoring/        # Resource monitoring (✅ Complete)
│   │   ├── base.py        # Monitoring architecture and abstractions
│   │   ├── resource_monitor.py  # System resource metrics
│   │   ├── trino_monitor.py     # Trino-specific metrics
│   │   ├── storage.py     # Time-series data storage
│   │   └── alerts.py      # Real-time alert system
│   ├── storage/           # Result storage (✅ Complete)
│   │   ├── models.py      # SQLAlchemy ORM models
│   │   ├── connection.py  # Database connection management
│   │   └── result_storage.py    # High-level storage API
│   ├── analysis/          # Result analysis (🔄 Phase 3.3)
│   └── utils/             # Utility functions
├── config/                # Hierarchical configuration
│   ├── reference.conf     # Framework defaults
│   ├── hosts/             # Host-specific configs
│   └── templates/         # System config templates
├── experiments/           # Experiment definitions (YAML)
├── systems/               # Running system installations
├── datasets/              # Generated datasets
├── results/               # Benchmark results (JSON)
├── downloads/             # Cached system binaries
└── tests/                 # Unit and integration tests
```

### Core Design Principles

1. **Separation of Concerns**: Each module has single responsibility
2. **Dependency Injection**: Systems and experiments are configurable
3. **Error Handling**: Comprehensive error handling with informative messages
4. **Extensibility**: Easy to add new systems, benchmarks, and metrics
5. **Testability**: All components are unit-testable with >80% coverage target
6. **Reproducibility**: Version-controlled configurations ensure repeatable experiments

---

## Project Timeline & Development Plan

### Completed Phases

**Phase 0-1 (Weeks 1-14)**: Foundation & Minimal Viable Framework ✅
- Python package structure with proper modules
- CLI system with Click framework (21 commands)
- Hierarchical HOCON configuration system
- Docker-based system management
- Experiment execution engine
- Testing infrastructure (123 tests passing)

**Phase 2.1 (Week 15)**: Extended Dataset Management ✅
- TPC-H data generation (SF1, SF10)
- Iceberg table format support:
  - PostgreSQL setup (Docker)
  - Hive Metastore integration (Docker)
  - MinIO object storage
  - Iceberg catalog configuration
  - Table creation and data loading

**Phase 2.2 (Week 16)**: TPC-H Benchmark Implementation ✅
- All 22 TPC-H queries implemented (`apps/tpch/queries/`)
- Multi-run execution with warmup support
- Query result validation (row counts, checksums)
- Experiment suites with hierarchical configuration
- Custom benchmark support

**Phase 3.1 (Weeks 18-20)**: Resource Monitoring ✅
- System resource monitoring (CPU, memory, disk, network)
- Trino metrics collection via REST API
- Query-level performance tracking
- Real-time alert system
- Time-series metrics storage (JSON, CSV)
- Comprehensive test suite (700+ lines)
- User documentation (MONITORING_GUIDE.md)

**Phase 3.2 (Weeks 21-25)**: Database Result Storage ✅
- SQLAlchemy ORM with 5 models (Experiment, ExperimentRun, QueryExecution, SystemMetric, MonitoringMetric)
- Dual database support (SQLite development, PostgreSQL production)
- Connection management with graceful fallback
- ResultStorage API with 17 methods
- Enhanced CLI commands (list, show, export, compare, delete, archive)
- Multi-format export (CSV, JSON, Parquet)
- Experiment integration with backward compatibility
- Comprehensive test suite (220+ lines)

### Current Phase

**Phase 3.3 (Weeks 26-27)**: Analysis Engine 🔄
- Statistical analysis (mean, median, stdev, percentiles)
- Performance regression detection
- Scalability analysis (speed-up, scale-up)
- Comparison analysis (baseline vs. current)
- HTML report generation with visualizations

### Upcoming Phases

**Phase 4 (Weeks 28-38)**: Kubernetes Cluster Deployment 📋
- Multi-node Trino cluster architecture
- Helm charts for Kubernetes
- Distributed monitoring
- School cluster deployment

**Phase 5 (Weeks 39-48)**: Framework Validation & Case Studies 📋
- Reproducibility testing
- Scalability experiments
- Performance case study (Iceberg vs Hive)
- TPC-H workload characterization

**Phase 6 (Optional)**: TPC-DS Benchmark Support 📋
- 20-30 representative TPC-DS queries
- Dataset generation and validation

**Phase 7 (Optional)**: Advanced Enhancements 📋
- Advanced workload orchestration
- Full hybrid HOCON+.env configuration
- Cloud deployment guides
- CI/CD integration

**Phase 8 (Concurrent)**: Dissertation Writing 📝
- Literature review, methodology, implementation chapters
- Evaluation with validation studies
- 10,000-15,000 words

### Phase 3 Completion Summary

**Phase 3.1 - Resource Monitoring (✅ Complete)**:
- 6 implementation modules (~2,100 lines)
- System and Trino metrics collection
- Real-time alerts and threshold monitoring
- Time-series data storage (JSON, CSV)
- Experiment integration with graceful degradation
- 3 unit test files (~700 lines)
- Complete user guide (MONITORING_GUIDE.md)
- Time: ~6 hours

**Phase 3.2 - Database Result Storage (✅ Complete)**:
- 5 SQLAlchemy models (Experiment, Run, Query, Metrics)
- Dual database support (SQLite + PostgreSQL)
- ResultStorage API (17 methods)
- Enhanced CLI commands (6 commands updated)
- Multi-format export (CSV, JSON, Parquet)
- Backward compatible with JSON files
- Comprehensive tests (~220 lines)
- Documentation (PHASE_3.2_RESULT_STORAGE.md)
- Time: ~6 hours

**Suite System Enhancements (✅ Complete - November 2025)**:
- Smart lifecycle management with status-based decision tree
- Enhanced three-layer Trino health verification
- Catalog-based dependency detection and auto-start
- Dependency-aware system startup ordering
- Template library (1,255 lines across 3 comprehensive reference files)
- Kubernetes deployment documentation (400+ lines)
- Code changes: ~200 lines in suite_commands.py and trino.py
- Documentation: 4 comprehensive files
- Time: ~8 hours

**Phase 3 Total**:
- ~5,200 lines of production code
- ~920 lines of test code
- 1,255 lines of template documentation
- 6 comprehensive documentation files
- 20 hours development time
- Production-ready monitoring, storage, and intelligent suite execution infrastructure

### Key Restructuring Decisions

1. **Research Focus Shifted**: Framework as primary contribution (not Iceberg study tool)
2. **Phase Reordering**: Monitoring (Phase 3) moved before Kubernetes (Phase 4) for better instrumentation
3. **Simplified Scope**: Phase 2.3 (orchestration) and full Phase 2.4 (hybrid config) deferred to Phase 7
4. **TPC-DS Optional**: TPC-H (22 queries) sufficient for framework validation
5. **Clean Dependencies**: TPC-H → Monitoring → Kubernetes → Validation

---

## Core Abstractions

### 1. System (`lib/tribench/core/system.py`)

Abstract base class for system components (Trino, PostgreSQL, MinIO, etc.).

**Interface**:
```python
class System(ABC):
    def setup() -> None          # Download, install, configure
    def start() -> None          # Launch with health checks
    def stop() -> None           # Graceful shutdown
    def teardown() -> None       # Complete cleanup
    def status() -> Dict         # Current runtime state
    @property
    def is_running() -> bool     # Quick health check
```

**Implementations**:
- `TrinoSystem` (✅ Complete): Docker-based Trino coordinator management
- `PostgreSQLSystem` (✅ Complete): Hive Metastore backend database
- `MinIOSystem` (✅ Complete): S3-compatible object storage for Iceberg
- `HiveMetastoreSystem` (✅ Complete): Iceberg catalog metadata management

**Key Features**:
- Docker Compose-based deployment for portability
- Health checking via HTTP endpoints
- Configuration-driven setup from HOCON
- Automatic binary download and caching
- Volume management for data persistence

### 2. Experiment (`lib/tribench/core/experiment.py`)

Abstract base class for benchmark experiments with structured lifecycle.

**Interface**:
```python
class Experiment(ABC):
    def prepare() -> None        # Validate and setup
    def run() -> Dict[str, Any]  # Execute workload
    def validate() -> bool       # Check results
    def cleanup() -> None        # Release resources
```

**ExperimentConfig** (Dataclass):
- `name`, `description`, `system` (required)
- `queries`, `query_files` (SQL workload)
- `runs`, `warmup_runs` (execution parameters)
- `timeout_seconds`, `max_retries` (failure handling)
- `connection` (system connection params)
- `validation` (result validation rules)
- `metrics` (metrics to collect)
- `metadata` (custom tags)

**Implementations**:
- `TrinoExperiment` (✅ Complete): SQL workload execution on Trino

**Key Features**:
- YAML-based experiment definitions
- Support for multiple runs with warmup phases
- Automatic retry with exponential backoff
- Comprehensive metrics collection
- Result validation against rules

### 3. Dataset (`lib/tribench/core/dataset.py`)

Abstract base class for benchmark datasets.

**Interface**:
```python
class Dataset(ABC):
    def generate() -> None            # Create dataset
    def validate() -> bool            # Check integrity
    def load(system: str) -> None     # Load into system
    def get_statistics() -> Dict      # Dataset stats
```

**DatasetMetadata** (Dataclass):
- `name`, `type` (static|generated)
- `format` (parquet|csv|iceberg)
- `size`, `location`, `tables`, `properties`

**Implementations** (🔄 Planned):
- TPC-H dataset generator (SF1, SF10)
- Iceberg table loader
- Dataset registry

### 4. Result (`lib/tribench/core/result.py`)

Dataclass representing experiment results with comprehensive metrics.

**Structure**:
```python
@dataclass
class Result:
    # Experiment metadata
    experiment_name: str
    experiment_type: str
    timestamp: datetime
    duration_seconds: float
    status: str  # success|failed|timeout
    
    # Query metrics
    execution_time: float
    cpu_time: float
    memory_usage: float
    data_scanned: int
    rows_returned: int
    
    # System metrics
    system_metrics: Dict[str, Any]
    
    # Validation
    validation_passed: bool
    validation_errors: List[str]
    
    # Additional context
    metadata: Dict[str, Any]
    error_message: str
    error_traceback: str
```

**Storage**: JSON files in `results/` directory
- Format: `{experiment-name}_{timestamp}.json`
- Human-readable and tool-friendly
- Enables incremental analysis

---

## Command-Line Interface

### CLI Architecture

Built with **Click** framework, organized into command groups:

```
tribench [OPTIONS] COMMAND [ARGS]...

Command Groups:
  sys     System lifecycle management (5 commands)
  exp     Experiment execution (5 commands)
  data    Dataset management (5 commands)  
  res     Result analysis (6 commands)
```

**Common Options**:
- `--dry-run`: Preview without execution
- `--verbose, -v`: Detailed logging
- `--config, -c <file>`: Custom config file
- `--help`: Command documentation

### System Management Commands (`sys`)

**Purpose**: Manage system component lifecycle (Trino, PostgreSQL, MinIO)

1. **`sys setup <system> [--version VERSION]`**
   - Downloads system binary (cached in `downloads/`)
   - Generates configuration files from HOCON templates
   - Creates Docker Compose setup
   - Prepares directories and networks
   
2. **`sys start <system>`**
   - Launches Docker containers via compose
   - Waits for health checks (HTTP endpoint polling)
   - Validates system readiness
   - Returns when system is operational

3. **`sys stop <system> [--force]`**
   - Graceful shutdown (default)
   - Force kill with `--force` flag
   - Stops containers but preserves volumes

4. **`sys status [system]`**
   - Shows running state
   - Health check status
   - Ports and endpoints
   - Container information

5. **`sys teardown <system> [--keep-data]`**
   - Requires confirmation (safety check)
   - Stops and removes containers
   - Deletes volumes
   - Optionally keeps config files with `--keep-data`

**Example Workflow**:
```bash
tribench sys setup trino --version 434
tribench sys start trino
tribench sys status trino
# ... run experiments ...
tribench sys stop trino
tribench sys teardown trino
```

### Experiment Commands (``)

**Purpose**: Execute benchmark experiments and monitor progress

1. **`exp run <file> [OPTIONS]`** (✅ Implemented)
   - Loads experiment config from YAML
   - Validates configuration
   - Executes queries with warmup and measured runs
   - Collects comprehensive metrics
   - Stores results as JSON
   - Options:
     - `--runs N`: Override number of runs
     - `--warmup N`: Override warmup runs
     - `--timeout SECONDS`: Query timeout
     - `--dry-run`: Show config without execution

2. **`exp list`** (🔄 Planned)
   - Lists available experiment definitions
   - Shows experiment metadata
   - Filters by benchmark type

3. **`exp status <id>`** (🔄 Planned)
   - Shows experiment progress
   - Live metrics during execution
   - Estimated time remaining

4. **`exp cancel <id>`** (🔄 Planned)
   - Gracefully stops running experiment
   - Preserves partial results
   - Cleanup resources

5. **`exp config <file>`** (🔄 Planned)
   - Shows resolved configuration
   - Displays merged HOCON hierarchy
   - Validates experiment definition

**Example Usage**:
```bash
tribench exp run experiments/tpch-q1-tiny.yaml --runs 3 --warmup 1
tribench exp run experiments/test-simple.yaml --verbose
```

### Dataset Commands (`data:`)

**Purpose**: Generate and manage benchmark datasets

1. **`data generate <dataset> [OPTIONS]`** (🔄 Planned)
   - Generates TPC-H datasets (SF1, SF10)
   - Supports multiple formats (CSV, Parquet)
   - Options:
     - `--scale-factor SF`: Data size
     - `--format FORMAT`: Output format
     - `--output PATH`: Target directory

2. **`data load <dataset> [OPTIONS]`** (🔄 Planned)
   - Loads dataset into system
   - Creates tables via SQL
   - Options:
     - `--system SYSTEM`: Target system
     - `--catalog CATALOG`: Trino catalog
     - `--format FORMAT`: Table format

3. **`data list`** (🔄 Planned)
   - Shows available datasets
   - Displays size and format
   - Shows loaded status

4. **`data info <dataset>`** (🔄 Planned)
   - Dataset metadata
   - Table schemas
   - Row counts and statistics

5. **`data validate <dataset>`** (🔄 Planned)
   - Checks data integrity
   - Validates row counts
   - Computes checksums

### Result Commands (`res:`)

**Purpose**: Analyze and visualize benchmark results

1. **`res show <id>`** (🔄 Planned)
   - Display experiment results
   - Summary statistics
   - Individual run details

2. **`res list [--experiment NAME]`** (🔄 Planned)
   - List stored results
   - Filter by experiment
   - Sort by date/status

3. **`res compare <ids...>`** (🔄 Planned)
   - Side-by-side comparison
   - Performance differences
   - Statistical significance

4. **`res export <id> [--format FORMAT]`** (🔄 Planned)
   - Export to CSV/JSON/Parquet
   - Integration with analysis tools

5. **`res analyze <suite>`** (🔄 Planned)
   - Aggregate suite results
   - Generate plots and charts
   - Statistical analysis

6. **`res delete <id>`** (🔄 Planned)
   - Remove result files
   - Cleanup storage

---

## Configuration System

### Hierarchical Configuration (HOCON)

**Three-Layer Architecture**:

1. **Layer 1 - Reference Config** (`config/reference.conf`)
   - Framework defaults
   - System versions (Trino: 434, PostgreSQL: 15)
   - Network ports (Trino: 8080, PostgreSQL: 5432)
   - Resource limits (JVM heap: 4G, query memory: 1GB)
   - Framework paths (datasets, results, systems)

2. **Layer 2 - Host Config** (`config/hosts/{hostname}/application.conf`)
   - Machine-specific overrides
   - Custom installation paths
   - Resource allocations
   - Auto-detected using `platform.node()`

3. **Layer 3 - Experiment Config** (experiment YAML files)
   - Experiment-specific settings
   - Query selection and parameters
   - Dataset and catalog configuration
   - Execution overrides

**Configuration Loading**:
```python
from tribench.utils.config import ConfigurationLoader

loader = ConfigurationLoader()
config = loader.load(
    experiment_config="experiments/tpch-sf1.yaml",
    host_name="localhost"  # Optional, auto-detected
)

# Access nested values
trino_port = config["tribench"]["systems"]["trino"]["coordinator"]["port"]
```

**Key Features**:
- **Hierarchical Merging**: Later layers override earlier ones
- **Environment Variables**: `${VAR_NAME}` and `${?VAR_NAME}` syntax
- **Validation**: Type checking, range validation, required fields
- **Templates**: Jinja2-based config file generation

### Configuration Validation

**Schema-Based Validation**:
```python
schema = {
    "tribench": {
        "required": True,
        "type": dict,
        "schema": {
            "version": {"type": str, "required": True},
            "systems": {
                "type": dict,
                "schema": {
                    "trino": {
                        "schema": {
                            "coordinator": {
                                "schema": {
                                    "port": {
                                        "type": int,
                                        "min": 1024,
                                        "max": 65535
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

errors = loader.validate(config, schema)
```

### Template Generation

**Jinja2 Templates** (`config/templates/`):
- `trino-config.properties.j2`: Trino coordinator configuration
- `trino-jvm.config.j2`: JVM settings and GC options
- Future: PostgreSQL, MinIO configs

**Usage**:
```python
from tribench.utils.config import ConfigurationTemplate

template_gen = ConfigurationTemplate()
config_content = template_gen.generate(
    "trino-config.properties.j2",
    config,
    output_path="systems/trino/etc/config.properties"
)
```

---

## Experiment Execution Engine

### Query Executor (`lib/tribench/experiments/query_executor.py`)

**Purpose**: Execute SQL queries against Trino with reliability and metrics collection

**Key Features**:
1. **Connection Management**
   - Automatic connection establishment
   - Connection state tracking with `is_connected()`
   - Graceful disconnect with error handling
   - Reconnection on transient failures

2. **Query Execution**
   ```python
   executor = QueryExecutor(
       host="localhost",
       port=8080,
       user="tribench",
       catalog="tpch",
       schema="tiny",
       timeout_seconds=300,
       max_retries=3
   )
   
   rows, metadata = executor.execute_query(
       "SELECT * FROM lineitem LIMIT 10",
       fetch_results=True
   )
   ```

3. **Retry Logic**
   - Automatic retry with exponential backoff
   - User errors (SQL syntax) don't trigger retries
   - System errors (network issues) retry up to max_retries
   - Backoff: 2^attempt seconds (max 30s)

4. **Metrics Collection**
   - Execution time (wall clock)
   - Query ID and state
   - CPU time and memory usage
   - Rows and bytes processed
   - Queued and scheduled time

5. **Error Handling**
   - `QueryExecutionError`: General execution failures
   - `QueryTimeoutError`: Timeout exceeded
   - Detailed error messages with context

### Result Collector (`lib/tribench/experiments/result_collector.py`)

**Purpose**: Store and aggregate experiment results

**Key Methods**:

1. **`create_result(experiment_name, duration, metadata, ...)`**
   - Builds Result object from execution data
   - Extracts Trino-specific metrics
   - Adds custom metadata tags

2. **`save_result(result)`**
   - Writes JSON to `results/{name}_{timestamp}.json`
   - Auto-creates results directory
   - Returns filepath for verification

3. **`load_result(filepath)`**
   - Reconstructs Result from JSON
   - Parses timestamp from ISO format

4. **`aggregate_results(results)`**
   - Computes statistics: mean, median, stdev, min, max
   - Success rate calculation
   - Returns aggregated metrics dict

5. **`generate_summary(results)`**
   - Human-readable report
   - Run count and success rate
   - Timing statistics

### Trino Experiment (`lib/tribench/experiments/trino_experiment.py`)

**Purpose**: Orchestrate complete experiment lifecycle

**Implementation Status**: ✅ Complete with experiment suites support (Week 16)

**Lifecycle**:

1. **Initialization**
   ```python
   config = ExperimentConfig.from_yaml("experiments/test-simple.yaml")
   experiment = TrinoExperiment(config, results_dir="results/")
   ```

2. **Prepare Phase**
   - Validates experiment configuration
   - Tests Trino connection
   - Verifies system readiness

3. **Execution Phase**
   - Collects queries (inline + files)
   - Executes warmup runs (if configured)
   - Runs measured iterations with timing
   - Collects per-query metrics
   - Aggregates statistics

4. **Validation Phase**
   - Checks success rate (default: ≥95%)
   - Row count validation against expected values
   - Result checksums for deterministic queries
   - Warns if variance exceeds threshold

5. **Cleanup Phase**
   - Disconnects from Trino
   - Releases resources

**Experiment Suites** (✅ New Feature):
- Hierarchical configuration merging
- Suite-level defaults with experiment overrides
- Example: `experiments/suites/tpch-suite.yaml`
- All 22 TPC-H queries organized in single suite

**Example Workflow**:
```python
try:
    experiment.prepare()
    results = experiment.run()
    valid = experiment.validate(results)
finally:
    experiment.cleanup()
```
   - Verifies system readiness

3. **Execution Phase**
   - Collects queries (inline + files)
   - Executes warmup runs (not measured)
   - Executes measured runs with metrics
   - Stores individual results as JSON
   - Aggregates statistics

4. **Validation Phase**
   - Checks success rate (default: ≥95%)
   - Calculates coefficient of variation
   - Warns if variance exceeds threshold

5. **Cleanup Phase**
   - Disconnects from Trino
   - Releases resources

**Example Workflow**:
```python
try:
    experiment.prepare()
    results = experiment.run()
    if experiment.validate():
        print("Experiment completed successfully")
    else:
        print("Validation failed")
finally:
    experiment.cleanup()
```

### Experiment Definition (YAML)

**Minimal Example**:
```yaml
name: "test-simple"
description: "Simple smoke test"
system: "trino"
connection:
  catalog: "tpch"
  schema: "tiny"
runs: 3
queries:
  - "SELECT COUNT(*) FROM nation"
```

**Complete Example**:
```yaml
name: "tpch-q1-sf1"
description: "TPC-H Query 1 at Scale Factor 1"
system: "trino"

connection:
  host: "localhost"
  port: 8080
  user: "tribench"
  catalog: "tpch"
  schema: "sf1"

runs: 5
warmup_runs: 2
timeout_seconds: 300
max_retries: 3

queries:
  - |
    SELECT
        l_returnflag,
        l_linestatus,
        SUM(l_quantity) AS sum_qty,
        AVG(l_quantity) AS avg_qty,
        COUNT(*) AS count_order
    FROM lineitem
    WHERE l_shipdate <= DATE '1998-09-02'
    GROUP BY l_returnflag, l_linestatus
    ORDER BY l_returnflag, l_linestatus

query_files:
  - "queries/tpch/q2.sql"
  - "queries/tpch/q3.sql"

validation:
  min_success_rate: 0.95
  max_execution_time_variance: 0.15

metrics:
  - execution_time
  - rows_returned
  - cpu_time
  - memory_usage
  - data_scanned

metadata:
  benchmark: "TPC-H"
  query_number: 1
  scale_factor: "sf1"
  expected_rows: 4
  tags: ["tpch", "aggregation", "production"]
```

---

### Suite System Enhancements (✅ November 2025)

#### Smart Lifecycle Management

**Purpose**: Intelligent system management with status-based decision making

**Implementation**: `lib/tribench/cli/suite_commands.py`

**Decision Tree**:
```
Check System Status
│
├─ Running & Healthy → Reuse (no action)
├─ Running & Unhealthy → Restart (stop + start)
└─ Not Running → Setup + Start
```

**Key Features**:
1. **Separate Tracking**:
   ```python
   already_running = []  # Pre-existing systems
   started_systems = []  # Systems started during suite
   ```

2. **Selective Cleanup**:
   - Only stops systems started during suite execution
   - Leaves pre-existing systems running
   - Prevents disrupting other work

3. **Status Verification**:
   - Checks system status before any action
   - Uses enhanced health checks (see Trino section)
   - Logs all decisions for transparency

#### Catalog-Based Dependency Detection

**Purpose**: Automatically detect and start required infrastructure based on experiment configuration

**Implementation**: `lib/tribench/cli/suite_commands.py` (lines 108-175)

**How It Works**:

1. **Inspect Experiment Configuration**:
   ```python
   for exp in experiments:
       catalog = exp.connection.get('catalog', '')
       
       if catalog == 'iceberg':
           required_system_names.update([
               'trino', 'hive-metastore', 'minio', 'postgresql'
           ])
   ```

2. **Catalog Mappings**:
   - `iceberg` → PostgreSQL + MinIO + Hive Metastore + Trino
   - `hive` → PostgreSQL + MinIO + Hive Metastore + Trino
   - `delta` / `hudi` → Similar lakehouse stack
   - `memory` / `tpch` → Trino only

3. **Dependency-Aware Ordering**:
   ```python
   system_order = ['postgresql', 'minio', 'hive-metastore', 'trino']
   
   systems_to_manage.sort(
       key=lambda s: system_order.index(s.name.split('-')[0])
       if s.name.split('-')[0] in system_order else 999
   )
   ```

**Benefits**:
- Users don't need to manually specify all dependencies
- Prevents "connection refused" errors from missing services
- Ensures correct startup order (dependencies before dependents)
- Works seamlessly with smart lifecycle management

**Example**:
```yaml
# Suite with Iceberg experiment
experiments:
  - name: "iceberg-query-1"
    connection:
      catalog: "iceberg"  # ← Automatically starts PostgreSQL, MinIO, HMS, Trino
      schema: "tpch"
```

#### Template Library

**Purpose**: Comprehensive reference templates for configuration

**Location**: `experiments/templates/`

**Suite Complete Reference** (`suite-template-complete-reference.yaml` - 355 lines):
- Every possible suite configuration option
- 10 example experiments showing different override patterns:
  1. Minimal experiment (only required fields)
  2. Execution parameter overrides
  3. Connection parameter overrides
  4. Validation overrides
  5. Monitoring overrides
  6. Metadata overrides
  7. Multiple override types
  8. Different system usage
  9. Inline queries
  10. Query files
- Configuration hierarchy explanation
- Validation rules documentation
- Monitoring configuration details
- Metadata and tagging guide

**Experiment Complete Reference** (`TEMPLATE-complete-reference.yaml` - 450 lines):
- All experiment fields documented with inline comments
- Connection parameters (basic and SSL/authentication)
- Execution parameters (runs, warmup, timeout, retries)
- Query configuration (inline SQL and file-based)
- Validation rules (success rate, variance, correctness)
- Monitoring configuration (resource and query metrics)
- Metrics collection options
- Metadata and tagging
- Advanced options

**Lakehouse Suite Template** (`suite-template-lakehouse.yaml` - 450 lines):
- 10 comprehensive testing phases:
  1. **Baseline Performance**: Standard TPC-H queries
  2. **Time Travel & Versioning**: Snapshot queries
  3. **Schema Evolution**: Column add/drop/rename
  4. **Partition Pruning**: Metadata optimization
  5. **Data Maintenance**: Compaction, snapshot expiration
  6. **Scalability Testing**: Multiple scale factors
  7. **Cross-Catalog Comparison**: Iceberg vs memory
  8. **Concurrent Query Performance**: Multi-user simulation
  9. **Write Performance**: INSERT, CTAS operations
  10. **Advanced Iceberg Features**: Merge-on-read, branching
- Iceberg-specific configuration
- Object storage metrics emphasis
- Time travel query examples
- Metadata table queries
- Best practices for lakehouse testing

---

## Dataset Management Module (✅ Phase 2.1 Complete)

### Overview

The dataset management module (`lib/tribench/data/`) provides comprehensive capabilities for generating, validating, loading, and tracking benchmark datasets. This module is critical for reproducible benchmarking and supports multiple data formats and scale factors.

**Implementation Status**: ✅ Complete (Week 15-16)
- All 5 core components implemented and tested
- 19 unit tests passing with good coverage
- CLI commands operational
- Dataset registry working

**Key Components**:
1. `DatasetMetadata`: Structured metadata storage ✅
2. `DatasetValidator`: Integrity and correctness validation ✅
3. `TPCHGenerator`: TPC-H dataset generation via Docker ✅
4. `TrinoDataLoader`: Loading datasets into Trino ✅
5. `DatasetRegistry`: Tracking and versioning datasets ✅
6. `IcebergLoader`: Iceberg table creation and data loading ✅

### DatasetMetadata (`lib/tribench/data/dataset.py`)

**Purpose**: Structured storage of dataset metadata for tracking and reproducibility

**Structure**:
```python
@dataclass
class DatasetMetadata:
    name: str                       # Dataset identifier
    type: str                       # 'static' or 'generated'
    format: str                     # 'parquet', 'csv', 'iceberg'
    scale_factor: Optional[float]   # TPC-H scale factor
    size_bytes: Optional[int]       # Total dataset size
    location: str                   # Filesystem path
    tables: List[str]               # Table names
    row_counts: Dict[str, int]      # Per-table row counts
    checksums: Dict[str, str]       # SHA256 checksums
    properties: Dict[str, Any]      # Custom properties
    created_at: str                 # ISO timestamp
    generator: Optional[str]        # Generator tool name
```

**Key Methods**:
- `to_dict()`: Serialize to dictionary for YAML storage
- `from_dict(data)`: Deserialize from dictionary

**Usage**:
```python
metadata = DatasetMetadata(
    name="tpch-sf1",
    type="generated",
    format="parquet",
    scale_factor=1.0,
    size_bytes=1024000000,
    location="/path/to/tpch-sf1/parquet",
    tables=["nation", "region", "customer", ...],
    row_counts={"nation": 25, "region": 5, ...},
    checksums={"nation": "abc123...", ...},
    properties={"tpch_version": "3.0"},
    created_at=datetime.now().isoformat(),
    generator="tpch-dbgen"
)
```

### DatasetValidator (`lib/tribench/data/dataset.py`)

**Purpose**: Validate dataset integrity and correctness

**Expected TPC-H Row Counts**:
```python
TPCH_ROW_COUNTS = {
    'tiny': {
        'nation': 25, 'region': 5, 'customer': 1500,
        'supplier': 100, 'part': 2000, 'partsupp': 8000,
        'orders': 15000, 'lineitem': 60175
    },
    '1': {
        'nation': 25, 'region': 5, 'customer': 150000,
        'supplier': 10000, 'part': 200000, 'partsupp': 800000,
        'orders': 1500000, 'lineitem': 6001215
    }
}
```

**Key Methods**:

1. **`compute_file_checksum(filepath: Path) -> str`**
   - Computes SHA256 checksum of a file
   - Returns: 64-character hex digest
   - Used for: Data integrity verification

2. **`validate_parquet_file(filepath: Path) -> Dict`**
   - Validates Parquet file structure
   - Returns: Dict with 'valid', 'row_count', 'schema', 'size_bytes', 'checksum'
   - Uses: PyArrow for parsing

3. **`validate_tpch_dataset(dataset_path: Path, scale_factor: str) -> Dict`**
   - Validates complete TPC-H dataset
   - Checks: File existence, Parquet validity, row counts
   - Returns: Dict with 'valid', 'tables', 'errors'

**Usage**:
```python
validator = DatasetValidator()

# Validate single Parquet file
result = validator.validate_parquet_file(Path("nation.parquet"))
if result['valid']:
    print(f"Valid file with {result['row_count']} rows")

# Validate complete TPC-H dataset
validation = validator.validate_tpch_dataset(
    Path("datasets/tpch-sf1/parquet"),
    scale_factor="1"
)

if validation['valid']:
    print("Dataset is valid")
else:
    for error in validation['errors']:
        print(f"Error: {error}")
```

### TPCHGenerator (`lib/tribench/data/dataset.py`)

**Purpose**: Generate TPC-H benchmark datasets using Docker-based dbgen

**Configuration**:
- Docker Image: `ghcr.io/scalytics/tpch-docker:latest`
- Supported Scale Factors: 0.01 (tiny), 1, 10, 100
- Output Formats: CSV, Parquet

**TPC-H Table Schemas**:
Complete PyArrow schemas defined for all 8 TPC-H tables:
- `nation`: 4 columns (n_nationkey, n_name, n_regionkey, n_comment)
- `region`: 3 columns (r_regionkey, r_name, r_comment)
- `customer`: 8 columns (c_custkey, c_name, c_address, ...)
- `supplier`: 7 columns (s_suppkey, s_name, s_address, ...)
- `part`: 9 columns (p_partkey, p_name, p_mfgr, ...)
- `partsupp`: 5 columns (ps_partkey, ps_suppkey, ps_availqty, ...)
- `orders`: 9 columns (o_orderkey, o_custkey, o_orderstatus, ...)
- `lineitem`: 16 columns (l_orderkey, l_partkey, l_suppkey, ...)

**Key Methods**:

1. **`generate(scale_factor: float, format: str) -> Path`**
   - Generates TPC-H dataset at specified scale
   - Steps:
     1. Create output directories
     2. Run dbgen via Docker (generates .tbl files)
     3. Convert CSV to Parquet (if format='parquet')
   - Returns: Path to generated dataset

2. **`_run_dbgen(scale_factor: float, output_dir: Path) -> None`**
   - Executes dbgen in Docker container
   - Command: `docker run --rm -v <output>:/data tpch-docker -s <SF>`
   - Error handling: Checks Docker availability, reports errors

3. **`_convert_to_parquet(csv_dir: Path, parquet_dir: Path) -> None`**
   - Converts .tbl files to Parquet
   - Uses PyArrow CSV reader with pipe delimiter
   - Applies proper schemas for type safety
   - Compression: Snappy

**Usage**:
```python
generator = TPCHGenerator(output_dir=Path("datasets"))

# Generate TPC-H SF1 in Parquet format
dataset_path = generator.generate(scale_factor=1.0, format='parquet')
# Result: datasets/tpch-sf1_0/parquet/ with 8 .parquet files

# Generate TPC-H tiny dataset
dataset_path = generator.generate(scale_factor=0.01, format='csv')
# Result: datasets/tpch-sf0_01/csv/ with 8 .tbl files
```

### TrinoDataLoader (`lib/tribench/data/dataset.py`)

**Purpose**: Load datasets into Trino catalogs

**Supported Catalogs**:
- Memory connector (for testing)
- Future: Iceberg, Hive connectors

**Key Methods**:

1. **`load_tpch_dataset(dataset_path: Path, catalog: str, schema: str) -> Dict[str, int]`**
   - Loads TPC-H Parquet files into Trino
   - Steps:
     1. Connect to Trino
     2. Create schema if not exists
     3. For each table: DROP IF EXISTS, CREATE TABLE, INSERT (placeholder)
   - Returns: Dict mapping table names to row counts

2. **`_generate_create_table_ddl(table_name: str, schema: pa.Schema) -> str`**
   - Generates CREATE TABLE DDL from PyArrow schema
   - Maps PyArrow types to Trino SQL types

3. **`_arrow_to_trino_type(arrow_type: pa.DataType) -> str`**
   - Type mappings:
     - `pa.int32()` → `INTEGER`
     - `pa.int64()` → `BIGINT`
     - `pa.string()` → `VARCHAR`
     - `pa.decimal128(p, s)` → `DECIMAL(p, s)`
     - `pa.date32()` → `DATE`
     - `pa.timestamp()` → `TIMESTAMP`

**Usage**:
```python
connection_params = {
    'host': 'localhost',
    'port': 8080,
    'user': 'admin'
}

loader = TrinoDataLoader(connection_params)

# Load TPC-H dataset into memory connector
row_counts = loader.load_tpch_dataset(
    dataset_path=Path("datasets/tpch-sf1/parquet"),
    catalog="memory",
    schema="tpch_sf1"
)

print(f"Loaded {sum(row_counts.values())} total rows")
for table, count in row_counts.items():
    print(f"  {table}: {count:,} rows")
```

**Note**: Current implementation creates empty tables (DDL only). Bulk data loading is planned for future releases.

### DatasetRegistry (`lib/tribench/data/dataset.py`)

**Purpose**: Track available datasets and their metadata

**Storage**: YAML file at `datasets/registry.yaml`

**Key Methods**:

1. **`register(metadata: DatasetMetadata) -> None`**
   - Register new dataset
   - Auto-saves to disk

2. **`get(name: str) -> Optional[DatasetMetadata]`**
   - Retrieve dataset metadata by name

3. **`list() -> List[DatasetMetadata]`**
   - List all registered datasets

4. **`delete(name: str) -> bool`**
   - Remove dataset from registry

5. **`update(name: str, metadata: DatasetMetadata) -> None`**
   - Update dataset metadata

**Usage**:
```python
registry = DatasetRegistry(Path("datasets/registry.yaml"))

# Register dataset
metadata = DatasetMetadata(...)
registry.register(metadata)

# List all datasets
for ds in registry.list():
    print(f"{ds.name}: {ds.format} @ {ds.location}")

# Get specific dataset
metadata = registry.get("tpch-sf1")
if metadata:
    print(f"Found: {metadata.name}")
```

### CLI Commands

**Five dataset management commands** implemented in `lib/tribench/cli/data_commands.py`:

1. **`tribench data generate <dataset>`**
   ```bash
   # Generate TPC-H SF1 in Parquet format
   tribench data generate tpch-sf1
   
   # Generate with options
   tribench data generate tpch-sf10 --format parquet --output /data/tpch
   
   # Overwrite existing dataset
   tribench data generate tpch-sf1 --overwrite
   ```
   
   **Options**:
   - `--format`: Output format (parquet, csv)
   - `--output`: Custom output directory
   - `--overwrite`: Replace existing dataset
   - `--dry-run`: Preview without executing
   
   **Output**:
   - Dataset generated message
   - Validation results
   - Summary: tables, total rows, total size
   - Registry confirmation

2. **`tribench data load <dataset>`**
   ```bash
   # Load dataset into memory connector
   tribench data load tpch-sf1
   
   # Load into specific catalog/schema
   tribench data load tpch-sf1 --catalog memory --schema benchmarks
   
   # Load with validation
   tribench data load tpch-sf1 --validate
   ```
   
   **Options**:
   - `--system`: Target system (trino)
   - `--catalog`: Trino catalog name
   - `--schema`: Schema/database name
   - `--validate`: Validate after loading
   
   **Output**:
   - Loading progress
   - Per-table row counts
   - Validation results (if --validate)

3. **`tribench data list`**
   ```bash
   # List all datasets
   tribench data list
   
   # Filter by pattern
   tribench data list --filter "tpch-sf*"
   
   # Show only generated datasets
   tribench data list --generated-only
   ```
   
   **Output**:
   - Dataset count
   - Per-dataset info: name, type, format, scale factor, tables, rows, size, location, created

4. **`tribench data info <dataset>`**
   ```bash
   # Show dataset information
   tribench data info tpch-sf1
   
   # Detailed mode with checksums
   tribench data info tpch-sf1 --detailed
   ```
   
   **Output**:
   - Metadata: type, format, scale factor, generator, location, created
   - Table list with row counts
   - Total size and rows
   - Properties and checksums (if --detailed)

5. **`tribench data validate <dataset>`**
   ```bash
   # Validate dataset structure
   tribench data validate tpch-sf1
   
   # Validate with checksums and row counts
   tribench data validate tpch-sf1 --checksums --row-counts
   ```
   
   **Options**:
   - `--checksums`: Verify file checksums
   - `--row-counts`: Verify row counts against metadata
   
   **Output**:
   - Validation status (pass/fail)
   - Per-check results
   - Error details if validation fails

### Configuration

**Dataset Configuration** (`config/reference.conf`):
```hocon
tribench {
  datasets {
    dir = ${tribench.app.path.datasets}
    registry = ${tribench.datasets.dir}"/registry.yaml"
    
    tpch {
      generator = "tpch-dbgen"
      docker_image = "ghcr.io/scalytics/tpch-docker:latest"
      version = "3.0.0"
      scale_factors = ["tiny", "1", "10", "100"]
      formats = ["parquet", "csv"]
      default_format = "parquet"
      
      row_counts {
        tiny { nation = 25, region = 5, ... }
        "1" { nation = 25, region = 5, ... }
      }
    }
    
    loading {
      batch_size = 1000
      parallel_tables = 1
      validate_after_load = true
    }
  }
}
```

### Testing

**Test Coverage**: 19 comprehensive tests in `tests/unit/test_dataset.py`

**Test Classes**:
1. `TestDatasetMetadata` (3 tests)
   - Metadata creation, serialization, deserialization

2. `TestDatasetValidator` (4 tests)
   - Expected row counts, checksum computation
   - Parquet validation (success and failure cases)

3. `TestTPCHGenerator` (3 tests)
   - Initialization, schema definitions
   - dbgen execution (success and Docker unavailable cases)

4. `TestTrinoDataLoader` (3 tests)
   - Initialization, type mappings, DDL generation

5. `TestDatasetRegistry` (6 tests)
   - Register, get, list, delete, update operations
   - Registry persistence to disk

**Running Tests**:
```bash
# Run all dataset tests
pytest tests/unit/test_dataset.py -v

# Run specific test class
pytest tests/unit/test_dataset.py::TestTPCHGenerator -v

# Run with coverage
pytest tests/unit/test_dataset.py --cov=lib/tribench/data --cov-report=html
```

### Known Limitations

1. **Data Loading**: Current implementation creates empty tables (DDL only). Bulk INSERT not implemented.
2. **Iceberg Support**: Planned for Phase 2.1
3. **CSV Format**: Supported in generation but not fully tested in loading
4. **Large Datasets**: SF100 may require significant Docker resources (20+ GB)
5. **Memory Connector**: Primary target; Hive and Iceberg connectors require additional setup

### Future Enhancements (Phase 2.1)

1. **Extended Scale Factors**: SF10, SF100 support
2. **Iceberg Tables**: Full Iceberg table format integration
3. **Hive Metastore**: Metadata storage integration
4. **MinIO Integration**: S3-compatible object storage
5. **Bulk Data Loading**: Efficient INSERT or COPY operations
6. **Custom Datasets**: Support for non-TPC-H datasets
7. **Dataset Versioning**: Track dataset versions and lineage
8. **PostgreSQL Support**: Load into PostgreSQL for comparisons

---

## System Implementations

### TrinoSystem (`lib/tribench/systems/trino.py`)

**Complete Docker-based Trino coordinator management** (✅ Implemented)

**Configuration** (from reference.conf):
```hocon
tribench.systems.trino {
  version = "434"
  coordinator {
    host = "localhost"
    port = 8080
    jvm {
      heap = "4G"
      opts = ["-server", "-XX:+UseG1GC"]
    }
  }
  catalogs {
    memory { connector = "memory" }
    tpch { 
      connector = "tpch"
      tpch.splits-per-node = 4
    }
    iceberg {
      connector = "iceberg"
      hive.metastore.uri = "thrift://localhost:9083"
      iceberg.catalog.type = "hive"
    }
  }
}
```

**Key Methods**:

1. **`setup(version=None)`**
   - Downloads Trino binary from Maven Central
   - Caches in `downloads/trino-server-{version}.tar.gz`
   - Generates config.properties, jvm.config, node.properties
   - Creates catalog configurations (memory, tpch, iceberg)
   - Builds Docker Compose file
   - Creates Docker network

2. **`start()`**
   - Launches container via `docker-compose up -d`
   - Waits for health check (polls `/v1/info`)
   - Validates startup (timeout: 120s)
   - Returns True when ready

3. **`stop(force=False)`**
   - Graceful: `docker-compose down`
   - Force: `docker-compose kill`
   - Preserves volumes

4. **`status()`**
   - Returns dict with:
     - `running`: bool
     - `healthy`: bool
     - `container_id`: str
     - `ports`: dict
     - `endpoints`: dict (UI, API)

5. **`teardown(keep_data=False)`**
   - Stops containers
   - Removes volumes
   - Optionally deletes config files

6. **`get_logs(tail=100, follow=False)`**
   - Retrieves Docker logs
   - Supports tail and follow modes

**Docker Compose Structure**:
```yaml
services:
  trino:
    image: trinodb/trino:{version}
    container_name: tribench-trino-{version}
    ports:
      - "{port}:8080"
    volumes:
      - ./etc:/etc/trino
      - trino-data:/data
    networks:
      - tribench-network
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/v1/info || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
```

**Health Checking** (✅ Enhanced November 2025):

**Three-Layer Verification** (lines 649-687):

The enhanced health check prevents premature experiment execution by verifying Trino is truly ready:

```python
def _check_health(self) -> bool:
    """Three-layer health verification"""
    url = f"http://{self.host}:{self.port}/v1/info"
    
    # Layer 1: HTTP endpoint responds
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return False
    except requests.RequestException:
        return False
    
    # Layer 2: Server not in starting state
    try:
        info = response.json()
        if info.get('starting', False):
            return False
    except (ValueError, KeyError):
        return False
    
    # Layer 3: Can execute queries
    try:
        from trino.dbapi import connect
        conn = connect(
            host=self.host,
            port=self.port,
            user='tribench'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False
```

**Why Three Layers?**:
1. **HTTP 200** confirms the service is running
2. **Starting field** confirms initialization is complete
3. **Query test** confirms the server can actually process queries

This prevents "SERVER_STARTING_UP" errors that occurred when experiments ran while Trino was still initializing internal components.

**Retry Logic**:
- Retries every 5 seconds for up to 120 seconds
- Returns True when all three checks pass
- Logs progress at each check

**Generated Configurations**:

1. **config.properties**:
   ```properties
   coordinator=true
   node-scheduler.include-coordinator=true
   http-server.http.port={port}
   discovery.uri=http://{host}:{port}
   query.max-memory=1GB
   query.max-memory-per-node=512MB
   ```

2. **jvm.config**:
   ```
   -server
   -Xmx{heap}
   -XX:InitialRAMPercentage=80
   -XX:MaxRAMPercentage=80
   -XX:+UseG1GC
   -XX:+HeapDumpOnOutOfMemoryError
   ```

3. **node.properties**:
   ```properties
   node.environment=tribench
   node.id={uuid}
   node.data-dir=/data/trino
   ```

---

## Testing Strategy

### Test Infrastructure

**Framework**: pytest with coverage reporting

**Current Status**: ✅ 123 tests passing (Week 16)
- Unit test coverage: ~43% (core components well-tested)
- Integration tests: 1 suite workflow test
- All tests passing in CI/CD

**Structure**:
```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (122 tests passing)
│   ├── test_cli.py         # CLI command tests
│   ├── test_config.py      # Configuration system tests
│   ├── test_config_hierarchy.py  # Hierarchical config tests
│   ├── test_dataset.py     # Dataset management tests (19 tests)
│   ├── test_experiment.py  # Experiment engine tests
│   ├── test_result.py      # Result model tests
│   └── test_system.py      # System abstraction tests
├── integration/             # Integration tests (1 test)
│   └── test_suite_workflow.py  # Experiment suite end-to-end test
└── fixtures/                # Test data
    ├── sample_config.conf
    ├── sample_experiment.yaml
    └── sample_results.json
```

**Test Coverage Highlights**:
- `lib/tribench/data/`: 69% coverage (19 unit tests)
- `lib/tribench/core/`: 85% coverage
- `lib/tribench/cli/`: 60% coverage
- `lib/tribench/experiments/`: 75% coverage
- `lib/tribench/utils/`: 80% coverage
    ├── sample_experiment.yaml
    └── sample_results.json
```

**Running Tests**:
```bash
# All tests
make test

# With coverage
make coverage

# Specific test file
pytest tests/unit/test_config.py -v

# Specific test function
pytest tests/unit/test_config.py::test_load_reference_config -v
```

### Test Coverage

**Current Coverage**: 80%+ target

**Coverage by Module**:
- `core/`: 85% (system, experiment, dataset, result)
- `cli/`: 75% (base, commands)
- `utils/config.py`: 84% (loader, templates, validation)
- `experiments/`: 78% (query_executor, result_collector, trino_experiment)
- `systems/trino.py`: 60% (manual testing heavy)

**Coverage Report**:
```bash
make coverage
open htmlcov/index.html
```

### Unit Tests

**Core Abstractions** (`test_system.py`, `test_experiment.py`):
- Abstract class instantiation
- Method signatures
- Property access

**Configuration System** (`test_config.py`):
- Reference config loading
- Host config auto-detection
- Experiment config parsing
- Hierarchical merging
- Validation (basic and schema)
- Template generation
- Environment variable substitution

**Experiment Engine** (`test_experiment.py`):
- ExperimentConfig YAML parsing
- QueryExecutor connection and execution (mocked)
- ResultCollector storage and aggregation
- TrinoExperiment lifecycle

**CLI** (`test_cli.py`):
- Command registration
- Argument parsing
- Help text generation
- Dry-run mode
- Error handling

### Integration Tests (Planned)

**End-to-End Workflow**:
1. Start Trino system
2. Load dataset
3. Run experiment
4. Validate results
5. Stop system

**System Integration**:
- Trino Docker setup
- Health check polling
- Query execution
- Log retrieval

**Data Pipeline**:
- Dataset generation (TPC-H)
- Data loading (CSV, Parquet)
- Table creation
- Data validation

---

## Kubernetes Integration (✅ Documentation Complete - November 2025)

### Overview

TriBench supports distributed Trino deployment on Kubernetes using **Kind** (Kubernetes in Docker). This enables testing multi-node cluster configurations locally before deploying to production environments.

**Documentation**: See `docs/KUBERNETES_KIND_SETUP.md` (400+ lines)

### Architecture

**Three-Tier Lakehouse Stack**:

1. **Compute Tier** (Trino):
   - 1 coordinator node (query planning, coordination)
   - 2 worker nodes (query execution)
   - Resource allocation: 3G heap, configurable CPU/memory limits

2. **Metadata Tier**:
   - PostgreSQL (Hive Metastore backend)
   - Hive Metastore (Iceberg catalog management)
   - Storage: 5Gi for PostgreSQL

3. **Storage Tier**:
   - MinIO (S3-compatible object storage)
   - Storage: 10Gi for object data

### Kind Cluster Configuration

**File**: `config/kubernetes/kind-cluster-config.yaml`

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: tribench
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080  # Trino UI
        hostPort: 8080
      - containerPort: 30900  # MinIO Console
        hostPort: 9000
  - role: worker
    labels:
      node-role: coordinator
  - role: worker
    labels:
      node-role: worker
```

**Features**:
- 3-node cluster: 1 control plane, 2 workers
- Port mappings for external access
- Node labels for workload scheduling
- Network configuration for inter-pod communication

### Kubernetes Configuration

**File**: `config/kubernetes/kind.conf`

**Trino Coordinator**:
```hocon
coordinator {
  replicas = 1
  resources {
    requests { memory = "4Gi", cpu = "2" }
    limits { memory = "6Gi", cpu = "4" }
  }
  jvm {
    heap = "3G"
    opts = ["-server", "-XX:+UseG1GC"]
  }
  nodeSelector {
    node-role = "coordinator"
  }
}
```

**Trino Workers**:
```hocon
workers {
  replicas = 2
  resources {
    requests { memory = "4Gi", cpu = "2" }
    limits { memory = "6Gi", cpu = "4" }
  }
  jvm {
    heap = "3G"
    opts = ["-server", "-XX:+UseG1GC"]
  }
  nodeSelector {
    node-role = "worker"
  }
}
```

**Supporting Services**:
- PostgreSQL: 2Gi memory, 1 CPU
- MinIO: 2Gi memory, 1 CPU
- Hive Metastore: 2Gi memory, 1 CPU

### Deployment Workflow

**Prerequisites**:
1. Docker Desktop or Docker Engine
2. kubectl (Kubernetes CLI)
3. Helm (package manager)
4. Kind (Kubernetes in Docker)

**Quick Start**:
```bash
# 1. Create Kind cluster
kind create cluster --config config/kubernetes/kind-cluster-config.yaml

# 2. Deploy infrastructure (via Helm charts - see KUBERNETES_KIND_SETUP.md)
# - PostgreSQL
# - MinIO
# - Hive Metastore
# - Trino (coordinator + workers)

# 3. Update TriBench configuration
# Edit config/hosts/kubernetes.conf with service endpoints

# 4. Run experiments
tribench exp run experiments/kubernetes-test.yaml
```

### TriBench Integration

**Connection Configuration**:
```hocon
tribench.systems.trino {
  coordinator {
    host = "localhost"  # Via NodePort mapping
    port = 30080        # Mapped from container port 8080
  }
  
  catalogs {
    iceberg {
      connector = "iceberg"
      hive.metastore.uri = "thrift://hive-metastore:9083"  # K8s service name
      iceberg.catalog.type = "hive"
    }
  }
}
```

**System Management**:
- Use `kubectl` commands for system lifecycle (start/stop/status)
- TriBench CLI still manages experiments and results
- Monitoring via Kubernetes dashboard and Trino Web UI

**Example Commands**:
```bash
# Check cluster status
kubectl get pods -A

# Check Trino status
kubectl get pods -l app=trino

# View Trino logs
kubectl logs -l app=trino -c coordinator

# Access Trino UI
# Open browser to http://localhost:30080

# Run TriBench experiment
tribench exp run experiments/kubernetes-test.yaml
```

### Monitoring

**Kubernetes Dashboard**:
- Resource usage per pod
- Network traffic
- Storage volumes
- Events and logs

**Trino Web UI** (`http://localhost:30080`):
- Active queries
- Query history
- Worker nodes status
- Cluster resource utilization

**TriBench Monitoring**:
- Same monitoring capabilities as Docker deployment
- System resource metrics collected from Kubernetes API
- Trino metrics via JMX/REST APIs

### Advantages

1. **Distributed Testing**: Test multi-node Trino configuration locally
2. **Resource Isolation**: Kubernetes resource limits and requests
3. **Scalability Testing**: Easy to adjust worker count
4. **Production Parity**: Similar to production Kubernetes deployments
5. **Educational**: Learn Kubernetes orchestration

### Current Status

- ✅ Kind cluster configuration complete
- ✅ Kubernetes HOCON configuration complete
- ✅ Comprehensive setup documentation (400+ lines)
- ✅ Integration guide with TriBench CLI
- ⚠️ Runtime testing pending (deployment and validation)
- 📋 Future: Full TriBench CLI integration with `kubectl` commands

### Next Steps

1. Deploy and validate Kind cluster setup
2. Run TPC-H benchmark suite on distributed Trino
3. Compare single-node vs distributed performance
4. Add Kubernetes-specific system commands to TriBench CLI
5. Extend to school cluster deployment (Phase 4)

---

## Development Workflow

### Environment Setup

1. **Create Conda Environment**:
   ```bash
   cd tribench-framework
   conda env create -f environment.yml
   conda activate tribench
   ```

2. **Install Package**:
   ```bash
   pip install -e .
   ```

3. **Verify Installation**:
   ```bash
   tribench --version
   pytest tests/
   ```

### Development Cycle

1. **Make Changes**: Edit code in `lib/tribench/`
2. **Run Tests**: `make test` or `pytest tests/`
3. **Check Coverage**: `make coverage`
4. **Format Code**: `make format` (black)
5. **Lint Code**: `make lint` (flake8)
6. **Manual Testing**: Use CLI commands
7. **Commit Changes**: Git with meaningful messages

### Makefile Commands

```bash
make help       # Show available commands
make install    # Install dependencies
make test       # Run all tests
make coverage   # Run tests with coverage
make lint       # Run linters
make format     # Format code with black
make clean      # Clean build artifacts
make cli ARGS='sys status trino'  # Run CLI directly
```

### Git Workflow

**Branch Structure**:
- `main`: Stable releases
- `develop`: Active development
- `feature/*`: Feature branches
- `bugfix/*`: Bug fixes

**Commit Messages**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Example**:
```
feat(systems): Add TrinoSystem implementation

- Docker Compose-based deployment
- Health checking via HTTP endpoint
- Configuration generation from HOCON
- Binary download and caching

Implements Phase 1, Section 1.3 of development plan
```

---

## Dependencies

### Core Dependencies

**Framework**:
- `python`: 3.11+ (type hints, dataclasses)
- `click`: 8.1.7 (CLI framework)
- `pyhocon`: 0.3.60 (HOCON configuration)
- `pyyaml`: 6.0.1 (YAML parsing)
- `jinja2`: 3.1.2 (template engine)

**Trino Integration**:
- `trino`: 0.325.0 (Python client)
- `requests`: 2.31.0 (HTTP health checks)

**Data Processing**:
- `pandas`: 2.1.0 (data analysis)
- `numpy`: 1.24.3 (numerical computing)
- `pyarrow`: 13.0.0 (Parquet support)

**Database**:
- `psycopg2-binary`: 2.9.7 (PostgreSQL driver)
- `sqlalchemy`: 2.0.21 (ORM)

**Monitoring** (planned):
- `psutil`: 5.9.5 (system metrics)
- `prometheus-client`: 0.17.1 (metrics export)

**Visualization** (planned):
- `matplotlib`: 3.7.2 (plotting)
- `seaborn`: 0.12.2 (statistical plots)
- `plotly`: 5.16.1 (interactive charts)

**Development**:
- `pytest`: 7.4.2 (testing framework)
- `pytest-cov`: 4.1.0 (coverage reporting)
- `pytest-mock`: 3.12.0 (mocking)
- `black`: 23.7.0 (code formatter)
- `flake8`: 6.0.0 (linter)
- `mypy`: 1.5.0 (type checker, optional)

**Docker**:
- `docker`: 6.1.3 (Python Docker client)
- `docker-compose`: via system installation

### Installation

**Via Conda** (recommended):
```bash
conda env create -f environment.yml
conda activate tribench
pip install -e .
```

**Via pip + venv**:
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## Key Design Decisions

### 1. Python as Implementation Language

**Rationale**:
- Rich ecosystem for data science and analysis
- Excellent libraries (pandas, numpy, matplotlib)
- Strong Trino client support
- Easy integration with Jupyter notebooks
- Popular in research community

**Trade-offs**:
- Performance overhead vs. Java/Scala
- GIL limitations for parallel execution
- Mitigated by: Subprocess-based parallelism, Docker orchestration

### 2. Docker-Based System Management

**Rationale**:
- Consistent environments across machines
- Easy setup and teardown
- No manual binary installation
- Health checks built-in
- Production-ready orchestration

**Trade-offs**:
- Docker dependency (not always available)
- Network overhead vs. native processes
- Mitigated by: Docker Desktop on macOS, Docker Engine on Linux

### 3. HOCON Configuration Format

**Rationale**:
- Human-friendly syntax (JSON-like with comments)
- Hierarchical merging built-in
- Environment variable substitution
- Includes and references
- Used by Apache projects (Spark, Flink)

**Trade-offs**:
- Less common than YAML/JSON
- Smaller ecosystem
- Mitigated by: Good pyhocon library, clear documentation

### 4. JSON Result Storage

**Rationale**:
- Human-readable for debugging
- Tool-friendly (jq, pandas, etc.)
- Schema flexibility
- Easy to version control
- No database dependency initially

**Trade-offs**:
- Not efficient for large datasets
- No indexing or querying
- Mitigated by: Future PostgreSQL integration, size limits

### 5. Click CLI Framework

**Rationale**:
- Professional command-line interface
- Command groups and subcommands
- Automatic help text generation
- Rich argument types and validation
- Context management

**Trade-offs**:
- More boilerplate than argparse
- Learning curve
- Mitigated by: Excellent documentation, common decorators

### 6. Test-Driven Development

**Rationale**:
- Catches bugs early
- Documents expected behavior
- Enables refactoring confidence
- Enforces good design
- Required for dissertation rigor

**Trade-offs**:
- Slower initial development
- Test maintenance overhead
- Mitigated by: Fixtures, mocking, CI integration

---

## Common Issues and Solutions

### Issue 1: Trino Container Not Starting

**Symptoms**:
- `tribench sys start trino` times out
- Health check fails
- Container exits immediately

**Diagnosis**:
```bash
docker ps -a | grep tribench-trino
docker logs tribench-trino-434
```

**Common Causes**:
1. Port 8080 already in use
   - Solution: Change port in `config/hosts/localhost/application.conf`
   - Or: Stop conflicting service

2. Insufficient memory
   - Solution: Reduce JVM heap in config (default: 4G)
   - Or: Increase Docker memory limit

3. Corrupted configuration
   - Solution: `tribench sys teardown trino` and re-setup
   - Check: `systems/trino-434/etc/config.properties`

### Issue 2: Query Execution Timeout

**Symptoms**:
- Queries timeout after 300 seconds
- `QueryTimeoutError` raised
- Partial results lost

**Solutions**:
1. Increase timeout in experiment YAML:
   ```yaml
   timeout_seconds: 600  # 10 minutes
   ```

2. Check Trino resource limits:
   ```sql
   SELECT * FROM system.runtime.queries;
   ```

3. Monitor system resources:
   ```bash
   docker stats tribench-trino-434
   ```

### Issue 3: Configuration Not Loading

**Symptoms**:
- Default values used instead of custom config
- Host config not found warning
- Environment variables not substituted

**Diagnosis**:
```python
from tribench.utils.config import ConfigurationLoader
loader = ConfigurationLoader()
config = loader.load()
print(config)
```

**Solutions**:
1. Check hostname: `python -c "import platform; print(platform.node())"`
2. Create host config: `config/hosts/{hostname}/application.conf`
3. Environment variables: `export VAR_NAME=value`

### Issue 4: Import Errors

**Symptoms**:
- `ModuleNotFoundError: No module named 'tribench'`
- Import paths not working
- Package not found

**Solutions**:
1. Reinstall in development mode:
   ```bash
   pip install -e . --force-reinstall
   ```

2. Check Python path:
   ```bash
   python -c "import sys; print(sys.path)"
   ```

3. Verify installation:
   ```bash
   pip show tribench
   ```

### Issue 5: Test Failures

**Symptoms**:
- Tests fail unexpectedly
- Coverage report errors
- Import errors in tests

**Solutions**:
1. Set PYTHONPATH:
   ```bash
   PYTHONPATH=lib:$PYTHONPATH pytest tests/
   ```

2. Clean cache:
   ```bash
   make clean
   pytest --cache-clear tests/
   ```

3. Update dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

---

## Future Development Roadmap

### Phase 2: Core Benchmarking (Weeks 11-16) 🔄

**Section 2.1: Extended Dataset Management**
- [ ] TPC-H data generation (dbgen integration)
- [ ] Scale factors: SF1, SF10, SF100
- [ ] Format support: CSV, Parquet, Iceberg
- [ ] Hive Metastore setup (Docker)
- [ ] MinIO object storage (S3-compatible)
- [ ] Dataset validation and checksums

**Section 2.2: Benchmark Implementation**
- [ ] TPC-H query suite (queries 1-10 initially)
- [ ] Query templating with Jinja2
- [ ] Parameter substitution
- [ ] Result validation (row counts, checksums)
- [ ] Custom benchmark support

**Section 2.3: Workload Definition**
- [ ] Workload YAML specification
- [ ] Query sequencing and timing
- [ ] Experiment suite support
- [ ] Execution orchestration

### Phase 3: Monitoring and Analysis (Weeks 17-22) 🔄

**Section 3.1: Resource Monitoring**
- [ ] System resource monitoring (psutil)
- [ ] Trino JMX metrics collection
- [ ] Query-level performance metrics
- [ ] Real-time monitoring
- [ ] Metrics storage (time-series)

**Section 3.2: Result Storage**
- [ ] PostgreSQL result database
- [ ] Schema design and migrations
- [ ] Result archiving and compression
- [ ] Data export (CSV, JSON, Parquet)

**Section 3.3: Analysis Engine**
- [ ] Statistical analysis (mean, median, stdev)
- [ ] Scalability analysis (speed-up, scale-up)
- [ ] Regression detection
- [ ] Comparison analysis
- [ ] Automated insights

**Section 3.4: Visualization**
- [ ] HTML report generation (Jinja2)
- [ ] Performance plots (matplotlib, plotly)
- [ ] Interactive dashboards
- [ ] Executive summaries
- [ ] Automated report pipeline

### Phase 4: Research Experiments (Weeks 23-28) 🔄

**Section 4.1: Iceberg Features Analysis**
- [ ] Iceberg catalog integration
- [ ] Time travel query experiments
- [ ] Schema evolution performance
- [ ] Partition pruning effectiveness
- [ ] Performance comparison: Memory vs. Iceberg

**Section 4.2: Experimental Validation**
- [ ] Reproducibility testing
- [ ] Variance analysis (<5% target)
- [ ] Result validation
- [ ] Statistical significance testing
- [ ] Anomaly detection

**Section 4.3: Documentation**
- [ ] User documentation
- [ ] Developer guides
- [ ] API documentation
- [ ] Example bundles
- [ ] Troubleshooting guide

### Phase 5: Advanced Features (Optional)

**Out of Scope for Dissertation**
- [ ] Multi-node Trino cluster
- [ ] Parallel experiment execution
- [ ] Cloud deployment (AWS, Azure, GCP)
- [ ] Kubernetes orchestration
- [ ] Machine learning analysis
- [ ] CI/CD integration

---

## Dissertation Integration

### Research Methodology

**Framework as Research Tool**:
1. **Experiment Design**: Structured YAML definitions
2. **Execution**: Automated, repeatable runs
3. **Data Collection**: Comprehensive metrics
4. **Analysis**: Statistical validation
5. **Reporting**: Visualizations and insights

**Reproducibility**:
- Version-controlled configurations
- Docker-based environments
- Documented procedures
- Shared result bundles

### Performance Evaluation

**Metrics Collected**:
- Query execution time (wall clock)
- CPU time and utilization
- Memory usage (peak, average)
- Data scanned (bytes, rows)
- Network I/O (for distributed setups)
- Disk I/O (reads, writes)

**Statistical Analysis**:
- Multiple runs per query (5-10 recommended)
- Warmup runs (2-3) to prime caches
- Outlier detection and removal
- Coefficient of variation (<15% target)
- Confidence intervals (95%)
- Statistical significance tests (t-test, ANOVA)

### Expected Results

**Iceberg Features Analysis**:
1. **Time Travel Performance**
   - Query overhead for historical snapshots
   - Impact of snapshot retention
   - Comparison with version tables

2. **Schema Evolution**
   - Performance of add/drop column operations
   - Impact on query execution
   - Comparison with ALTER TABLE

3. **Partition Pruning**
   - Effectiveness of partition filters
   - Query speedup ratios
   - Optimal partition strategies

4. **Format Comparison**
   - Memory connector (baseline)
   - CSV files (simplest)
   - Parquet files (columnar)
   - Iceberg tables (full features)

**Deliverables**:
- Performance charts and tables
- Statistical analysis results
- Optimization recommendations
- Best practices guide

---

## Documentation Index

### User Documentation
- `README.md`: Project overview and quick start
- `GETTING_STARTED.md`: Detailed setup instructions
- `experiments/README.md`: Experiment definition guide
- `config/README.md`: Configuration system guide

### Developer Documentation
- `IMPLEMENTATION_PLAN.md`: Development roadmap
- `lib/tribench/*/README.md`: Module-specific docs
- Docstrings: All classes and methods
- `Journal.md`: Development log

### API Documentation
- `lib/tribench/core/`: Abstract base classes
- `lib/tribench/cli/`: Command-line interface
- `lib/tribench/systems/`: System implementations
- `lib/tribench/experiments/`: Experiment engine
- `lib/tribench/utils/`: Utility functions

### Examples
- `experiments/test-simple.yaml`: Smoke test
- `experiments/tpch-q1-tiny.yaml`: TPC-H Query 1
- `config/hosts/localhost/`: Local development config

---

## Change Log

### Version 1.0.0-dev (Current)

**Phase 0: Foundation (Complete)** ✅
- Package structure and abstractions
- Testing infrastructure (49+ unit tests)
- Development environment setup

**Phase 1: Minimal Viable Framework (Sections 1.1-1.4 Complete)** ✅

**Section 1.1: CLI (Complete)** ✅
- 21 commands across 4 groups
- Common options (dry-run, verbose, config)
- Help system and documentation
- Error handling

**Section 1.2: Configuration System (Complete)** ✅
- Hierarchical HOCON configuration
- Three-layer merging (reference, host, experiment)
- Validation with custom schemas
- Jinja2 template generation
- Environment variable substitution

**Section 1.3: System Management (Complete)** ✅
- TrinoSystem implementation
- Docker Compose-based deployment
- Health checking and status monitoring
- Binary download and caching
- Configuration file generation

**Section 1.4: Experiment Engine (Complete)** ✅
- QueryExecutor with Trino client integration
- ResultCollector for storage and aggregation
- TrinoExperiment lifecycle implementation
- YAML-based experiment definitions
- Retry logic and error handling

**Known Issues**:
- Integration tests not yet implemented
- Result commands (res:*) not implemented
- Dataset generation not implemented
- PostgreSQL and MinIO systems pending

---

## Contact and Support

**Author**: Adam Yuan  
**Email**: [your.email@glasgow.ac.uk]  
**Institution**: University of Glasgow  
**Program**: MSc Computer Science  
**Project**: Dissertation - Benchmarking SQL Workloads on Data Lakehouses

**Repository**: [GitHub URL]  
**Issues**: [GitHub Issues URL]  
**Documentation**: [GitHub Wiki URL]

---

## Appendix: Code Statistics

**Total Lines of Code**: ~20,000+
- Core framework: ~7,000
- Tests: ~4,000
- Configuration: ~1,000
- Documentation: ~8,000

**Test Coverage**: 43% overall (core components 70%+)
- Unit tests: 122 test cases passing
- Integration tests: 1 test (suite workflow)
- Dataset tests: 19 comprehensive tests
- All tests passing

**Development Time**: ~100+ hours (estimated)
- Phase 0-1: ~70 hours
- Phase 2.1 (Iceberg): ~15 hours
- Phase 2.2 (TPC-H): ~15 hours
- Documentation: ~10 hours

**Files Created**: 150+
- Python modules: 50+
- Test files: 20+
- Configuration files: 15+
- Documentation files: 15+
- Experiment definitions: 10+
- TPC-H queries: 22 SQL files
- System configurations: Multiple

---

## Implementation Status Summary

### ✅ Completed Features (Weeks 1-16)

**Core Framework**:
- ✅ Abstract base classes (System, Experiment, Dataset, Result)
- ✅ Python package structure with proper modules
- ✅ 123 passing tests with pytest infrastructure

**CLI System**:
- ✅ 21 commands across 4 groups (sys, exp, data, res)
- ✅ Click-based interface with help documentation
- ✅ Dry-run and verbose modes

**Configuration**:
- ✅ Hierarchical HOCON configuration (reference → host → experiment)
- ✅ Environment variable substitution
- ✅ Jinja2 template generation
- ✅ Schema validation

**System Management**:
- ✅ TrinoSystem: Docker-based coordinator
- ✅ PostgreSQLSystem: Hive Metastore backend
- ✅ MinIOSystem: S3-compatible object storage
- ✅ HiveMetastoreSystem: Iceberg catalog

**Experiment Engine**:
- ✅ Query executor with retry logic
- ✅ Result collector with aggregation
- ✅ Multi-run execution with warmup
- ✅ Experiment suites with hierarchical config
- ✅ Result validation (row counts, checksums)

**Dataset Management**:
- ✅ TPC-H dataset generation (Docker-based dbgen)
- ✅ Parquet conversion with PyArrow
- ✅ Dataset validation and checksums
- ✅ Dataset registry (YAML-based)
- ✅ Iceberg table creation and loading
- ✅ All 5 CLI commands (generate, load, list, info, validate)

**Benchmarks**:
- ✅ All 22 TPC-H queries implemented
- ✅ TPC-H scale factors: SF0.01 (tiny), SF1, SF10
- ✅ Query result validation
- ✅ Multiple runs with statistics

### 🔄 In Progress / Upcoming (Weeks 17+)

**Phase 2.4 (Week 17)**: Secrets Management
- 🔄 .env configuration for credentials
- 🔄 python-dotenv integration
- 🔄 Security documentation

**Phase 3 (Weeks 18-27)**: Monitoring & Analysis
- 📋 Resource monitoring (CPU, memory, I/O)
- 📋 Trino JMX metrics
- 📋 Query plan collection
- 📋 PostgreSQL result storage
- 📋 Statistical analysis
- 📋 HTML report generation
- 📋 Visualization (matplotlib, plotly)

**Phase 4 (Weeks 28-38)**: Kubernetes Cluster
- 📋 Multi-node architecture
- 📋 Helm charts
- 📋 Distributed monitoring
- 📋 School cluster deployment

**Phase 5 (Weeks 39-48)**: Validation & Case Studies
- 📋 Reproducibility testing
- 📋 Scalability experiments
- 📋 Iceberg vs Hive performance study
- 📋 TPC-H workload analysis

**Phase 6-7 (Optional)**: Enhancements
- 📋 TPC-DS benchmark (20-30 queries)
- 📋 Advanced orchestration
- 📋 Full hybrid configuration
- 📋 Cloud deployment
- 📋 CI/CD integration

**Phase 8 (Concurrent)**: Dissertation
- 📝 Literature review
- 📝 Methodology chapter
- 📝 Implementation chapter
- 📝 Evaluation with studies
- 📝 10,000-15,000 words

### Recent Enhancements (Week 26 - November 2025)

**Smart Lifecycle Management** ✅:
- Status-based decision tree: reuse (healthy), restart (unhealthy), setup+start (not running)
- Separate tracking of pre-existing vs newly-started systems
- Selective cleanup: only stop what was started during suite execution
- Implemented in `lib/tribench/cli/suite_commands.py`

**Enhanced Health Verification** ✅:
- Three-layer Trino health check:
  1. HTTP endpoint check (`/v1/info` returns 200)
  2. Server state check (JSON `starting` field is false)
  3. Query execution test (`SELECT 1` succeeds)
- Prevents "SERVER_STARTING_UP" race condition
- Implemented in `lib/tribench/systems/trino.py` (lines 649-687)

**Catalog-Based Dependency Detection** ✅:
- Automatically inspects `experiment.connection.catalog` field
- Maps catalogs to required infrastructure:
  - `iceberg`/`hive` → PostgreSQL + MinIO + Hive Metastore + Trino
  - `delta`/`hudi` → Similar lakehouse stack
  - `memory`/`tpch` → Trino only
- Dependency-aware startup ordering: PostgreSQL → MinIO → HMS → Trino
- Implemented in `lib/tribench/cli/suite_commands.py` (lines 108-175)

**Template Library** ✅:
- `experiments/templates/suite-template-complete-reference.yaml` (355 lines)
  - Every possible suite configuration option
  - 10 example experiments showing different override patterns
  - Configuration hierarchy and validation rules
- `experiments/templates/TEMPLATE-complete-reference.yaml` (450 lines)
  - Complete experiment configuration reference
  - All fields documented with inline comments
- `experiments/templates/suite-template-lakehouse.yaml` (450 lines)
  - 10 testing phases for lakehouse architecture
  - Time travel, schema evolution, partition pruning
  - Iceberg-specific features and maintenance operations

**Kubernetes Documentation** ✅:
- `docs/KUBERNETES_KIND_SETUP.md` (400+ lines)
  - Architecture overview (3-tier: compute, metadata, storage)
  - Setup instructions (Kind, kubectl, Helm)
  - Deployment procedures for all components
  - Monitoring and troubleshooting guides
- `config/kubernetes/kind-cluster-config.yaml` (3-node cluster config)
- `config/kubernetes/kind.conf` (complete K8s configuration)
- Distributed Trino: 1 coordinator + 2 workers in Kind cluster

### Known Limitations

1. **Data Loading**: Iceberg loader creates tables but bulk INSERT not fully tested at scale
2. **Cluster**: Single-node Docker tested, Kubernetes deployment documented but not fully validated
3. **TPC-DS**: Not implemented (optional Phase 6)
4. **Result Analysis**: Basic aggregation only (advanced analytics in Phase 3.3)

### Next Immediate Steps

1. **Week 17**: Implement secrets management (.env configuration)
2. **Week 18**: Begin Phase 3 monitoring infrastructure
3. **Apply for School Cluster Access**: Required for Phase 4 (Week 28+)
4. **Continue Testing**: Increase coverage to 70%+ overall

---

## Quick Reference Commands

```bash
# Environment Setup
conda activate tribench
pip install -e .

# System Management
tribench sys setup trino --version 434
tribench sys start trino
tribench sys status trino
tribench sys stop trino

# Run Experiments
tribench exp run experiments/test-simple.yaml
tribench exp run experiments/tpch-q1-tiny.yaml --runs 5

# Development
make test          # Run tests
make coverage      # Coverage report
make format        # Format code
make lint          # Lint code

# Docker Management
docker ps | grep tribench
docker logs tribench-trino-434
docker-compose -f systems/trino-434/docker-compose.yml down

# Results
ls -lh results/
cat results/test-simple_*.json | jq .
```

---

**End of Context Document**

*This context file provides a comprehensive overview of the TriBench framework for AI agents working on this codebase. It includes architecture, implementation details, usage patterns, and development guidelines. Last updated: October 17, 2025.*
