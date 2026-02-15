# TriBench - Trino Benchmarking Framework

A framework for benchmarking SQL workloads on distributed data lakehouses using Apache Trino, inspired by the PEEL framework architecture.

## Overview

TriBench provides a systematic approach to:
- **Define** benchmark experiments with structured configurations
- **Execute** SQL workloads on Trino clusters with proper lifecycle management
- **Monitor** hardware resource usage and system performance
- **Analyze** results with structured reporting and visualization
- **Share** reproducible benchmark bundles

## Architecture

This framework follows a bundle-based architecture similar to PEEL:

```
tribench-framework/
├── bin/                    # Command-line interface
├── apps/                   # Benchmark applications and SQL workloads
├── config/                 # Environment and experiment configurations
├── datagens/              # Data generators (TPC-DS, TPC-H, custom)
├── datasets/              # Static datasets
├── downloads/             # System binaries and archives
├── lib/                   # Framework libraries
├── log/                   # Execution logs
├── results/               # Benchmark results and reports
├── systems/               # Running system installations
└── utils/                 # Utility scripts and tools
```

## Prerequisites

### Foundation Tools (Required for All Users)

**macOS Users:**
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Xcode Command Line Tools (provides git, compilers, etc.)
xcode-select --install

# Install Git (if not included in Xcode tools)
brew install git
```

**Verify Foundation Setup:**
```bash
brew --version                      # Should show Homebrew version
git --version                       # Should show Git version
```

### Backend-Specific Dependencies

Before setting up TriBench, install the required backend tools:

**Required (Docker Backend):**
```bash
brew install --cask docker          # Docker Desktop (includes Docker Compose)
```

**Required (Kubernetes Backend):**
```bash
brew install kubectl                # Kubernetes CLI
brew install helm                   # Helm package manager for Kubernetes
```

**Optional (Local Kubernetes Development):**
```bash
brew install kind                   # Kind (Kubernetes in Docker)
```

**Optional (GCP/GKE Deployments):**
```bash
brew install --cask google-cloud-sdk  # gcloud CLI for GCP
```

**Optional (MinIO S3 Operations):**
```bash
brew install minio/stable/mc        # MinIO Client for S3 operations
```

### Verify Docker Installation
```bash
docker --version                    # Should show Docker version
docker compose version              # Should show Docker Compose version
```

## Quick Start

1. **Setup Environment:**
   ```bash
   # Setup Python environment with Conda
   conda env create -f environment.yml
   conda activate tribench
   
   # Install TriBench in development mode
   pip install -e .
   
   # Verify installation
   tribench --version
   ```

2. **Configure Backend (Docker or Kubernetes):**
   
   TriBench supports both Docker Compose and Kubernetes backends. Configure your preferred backend once:
   
   ```bash
   # For local development (Docker Compose - default)
   tribench config profile local
   
   # For local Kubernetes (kind cluster)
   tribench config profile kind
   
   # For GCP/GKE deployments
   tribench config profile gcp-gke
   
   # Check active configuration
   tribench config show
   ```
   
   The backend configuration is stored in `config/hosts/<profile>.conf` and controls:
   - System deployment method (Docker Compose vs Kubernetes)
   - Connection endpoints and ports
   - Resource allocation settings
   
   **Note:** All commands (`sys`, `data`, `exp`, `suite`) automatically use the configured backend.

3. **Configure Systems:**
   ```bash
   # Setup infrastructure for Iceberg support
   tribench sys setup postgresql
   tribench sys setup minio
   tribench sys setup hive-metastore
   
   # Setup and start Trino with Iceberg catalog
   tribench sys setup trino
   tribench sys start trino
   
   # Check system status
   tribench sys status trino
   tribench sys status hive-metastore
   ```

4. **Run Benchmark:**
   ```bash
   # Execute an experiment
   tribench exp run experiments/tpch-sf1.yaml
   
   # Run with dry-run mode
   tribench exp run experiments/tpch-sf1.yaml --dry-run
   
   # Run with multiple iterations
   tribench exp run experiments/tpch-sf1.yaml --runs 3 --warmup 1
   ```

5. **Analyze Results:**
   ```bash
   # Show experiment results
   tribench res show exp-001
   
   # List all results
   tribench res list
   
   # Analyze suite results
   tribench res analyze tpch-sf1 --report detailed
   
   # Export results
   tribench res export exp-001 --format csv
   ```

## Command Line Interface

TriBench provides a comprehensive CLI with the following command groups:

### System Management (`sys`)
```bash
tribench sys setup <system>      # Setup a system (trino, postgresql, minio, hive-metastore)
tribench sys start <system>      # Start a system
tribench sys stop <system>       # Stop a system
tribench sys status <system>     # Check system status
tribench sys teardown <system>   # Tear down a system
tribench sys logs <system>       # View system logs
```

### Experiment Execution (`exp`)
```bash
tribench exp run <file>          # Execute an experiment
tribench exp list                # List available experiments
tribench exp status <id>         # Check experiment status
tribench exp cancel <id>         # Cancel running experiment
tribench exp config <file>       # Show experiment configuration
```

### Experiment Suites (`suite`)
```bash
tribench suite run <file>        # Execute all experiments in a suite
tribench suite list              # List available experiment suites
tribench suite show <file>       # Show suite details and configuration
```

### Dataset Management (`data`)
```bash
tribench data generate <dataset> # Generate a dataset (tpch-sf1, etc.)
tribench data load <dataset>     # Load dataset into system
tribench data load-iceberg <dataset>  # Load dataset into Iceberg tables
tribench data list               # List available datasets
tribench data info <dataset>     # Show dataset information
tribench data validate <dataset> # Validate dataset integrity
tribench data validate-iceberg   # Validate Iceberg tables
```

### Result Analysis (`res`)
```bash
tribench res show <id>           # Show experiment results
tribench res list                # List all results
tribench res compare <ids...>    # Compare multiple results
tribench res export <id>         # Export results to file
tribench res analyze <suite>     # Analyze suite results
tribench res delete <id>         # Delete experiment results
```

### Common Options
```bash
--dry-run                        # Show what would be done without executing
--verbose, -v                    # Enable verbose output
--config, -c <file>              # Specify configuration file
--help                           # Show command help
```

### Examples

```bash
# Setup infrastructure stack for Iceberg
tribench sys setup postgresql --dry-run
tribench sys setup minio
tribench sys setup hive-metastore
tribench sys start postgresql
tribench sys start minio
tribench sys start hive-metastore

# Setup and start Trino with Iceberg catalog
tribench sys setup trino --version 434 --dry-run
tribench sys start trino --verbose

# Generate and load TPC-H data into Iceberg
tribench data generate tpch-sf1 --format parquet
tribench data load-iceberg tpch-sf1 --catalog iceberg --schema tpch
tribench data load-iceberg tpch-sf1 --no-partition --validate
tribench data validate-iceberg --scale-factor 1 --detailed

# View Iceberg dataset metadata
tribench data list
tribench data info tpch-sf1-iceberg
tribench data info tpch-sf1-iceberg --detailed

# Run individual experiments
tribench exp run experiments/tpch-sf1.yaml --runs 3
tribench exp status exp-001 --follow

# Run experiment suites
tribench suite run experiments/suites/tpch-suite.yaml
tribench suite run experiments/suites/tpch-suite.yaml --runs 5 --timeout 600
tribench suite run experiments/suites/tpch-suite.yaml --filter "q1,q6" --dry-run
tribench suite show experiments/suites/tpch-suite.yaml

# Analyze results
tribench res compare exp-001 exp-002 exp-003
tribench res analyze tpch-sf1 --report performance --plot
tribench res export exp-001 --format json --output results.json

# System management
tribench sys status trino
tribench sys logs hive-metastore --tail 50
tribench sys stop trino
tribench sys teardown minio
```

## Supported Systems

- **Apache Trino**: Distributed SQL query engine (v434+)
- **Apache Iceberg**: Open table format for data lakehouses with full integration
- **Apache Hive Metastore**: Catalog service for Iceberg table metadata (v4.0.0)
- **MinIO**: S3-compatible object storage for Iceberg table data
- **PostgreSQL**: Metastore backend and results database (v15)
- **Grafana**: Monitoring and visualization (optional)

## Supported Benchmarks

- **TPC-H**: Decision support benchmark
- **TPC-DS**: Data warehousing benchmark  
- **Custom SQL**: User-defined workloads
- **Microbenchmarks**: Individual query performance tests

## Key Features

- **Structured Experiment Definition**: YAML-based experiment configurations
- **Experiment Suites**: Group related experiments with shared configuration defaults
- **Configuration Hierarchy**: Environment variables → Config files → Defaults
- **Cloud-Agnostic Deployment**: Works on Kind (local), GKE, AKS, EKS without code changes
- **Environment Management**: Host-specific configurations and system lifecycle
- **Apache Iceberg Integration**: Full support for Iceberg tables with metadata tracking
  - Automated catalog configuration with Hive Metastore
  - Data loading from Parquet to Iceberg format
  - Snapshot and versioning support
  - Comprehensive validation framework
  - Registry-based metadata persistence
- **Resource Monitoring**: CPU, memory, I/O, and network usage tracking
- **Kubernetes Monitoring**: Pod-level metrics collection for cloud deployments
- **Result Storage**: Structured storage in databases for analysis
- **Reproducibility**: Version-controlled bundles for sharing
- **Extensibility**: Plugin architecture for custom benchmarks

## Configuration

TriBench uses a hierarchical configuration system that allows deployment across different environments without code changes.

### Configuration Priority

Values are resolved in this order (highest to lowest):

1. **Environment Variables** (highest priority)
2. **Configuration Files** (via `--config` flag)
3. **Hardcoded Defaults** (fallback)

### Environment Variables

**Kubernetes Configuration:**
```bash
# Override Kubernetes context
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"

# Override namespace
export TRIBENCH_K8S_NAMESPACE="production"
```

**Quick Examples:**
```bash
# Local development (Docker Compose - default)
tribench config profile local
tribench sys setup all

# Local Kubernetes (kind cluster)
tribench config profile kind
tribench sys setup all

# Google Cloud (GKE)
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"
tribench config profile gcp-gke
tribench sys setup all

# Azure (AKS)
export TRIBENCH_K8S_CONTEXT="aks-tribench-cluster"
tribench config profile azure-aks
tribench sys setup all

# AWS (EKS)
export TRIBENCH_K8S_CONTEXT="arn:aws:eks:us-east-1:123456789012:cluster/tribench"
tribench config profile aws-eks
tribench sys setup all
```

For complete configuration documentation, see [CONFIGURATION.md](docs/CONFIGURATION.md).

## Experiment Suites

TriBench supports grouping related experiments into suites with shared configuration:

```yaml
# experiments/suites/tpch-suite.yaml
name: tpch-suite
description: TPC-H benchmark queries with suite-level defaults

defaults:
  system: trino
  runs: 3
  warmup_runs: 1
  timeout_seconds: 300
  validation:
    min_success_rate: 0.95

experiments:
  - path: ../tpch-q1-tiny.yaml
    # Uses all suite defaults
  
  - path: ../test-simple.yaml
    timeout_seconds: 60  # Override just this field
  
  - path: ../tpch-q1-sf1.yaml
    runs: 10  # More runs for larger dataset
    warmup_runs: 2
```

**Configuration Precedence** (highest precedence last):
1. Global defaults (in framework)
2. Suite defaults (from suite YAML)
3. Experiment YAML (individual experiment file)
4. CLI overrides (command-line flags)

**Running Suites**:
```bash
# Run all experiments in suite
tribench suite run experiments/suites/tpch-suite.yaml

# Override suite/experiment settings via CLI (applies to all experiments)
tribench suite run experiments/suites/tpch-suite.yaml --runs 10 --timeout 1200

# Run only specific experiments from suite
tribench suite run experiments/suites/tpch-suite.yaml --filter "q1,q6,q17"

# Preview configuration without execution
tribench suite run experiments/suites/tpch-suite.yaml --dry-run
```

See `CONFIG_HIERARCHY.md` for complete documentation on configuration merging behavior.

## Apache Iceberg Integration

TriBench provides comprehensive support for Apache Iceberg tables with full metadata tracking and versioning capabilities.

### Infrastructure Stack

The Iceberg integration consists of four interconnected systems:

```
Trino (Query Engine)
  ↓ queries
Iceberg Catalog (Hive Metastore)
  ↓ metadata storage         ↓ data location
PostgreSQL                 MinIO (S3A)
  (table schemas,            (Parquet files,
   partitions,               data files,
   statistics)               manifest files)
```

### Setup Iceberg Infrastructure

```bash
# 1. Setup PostgreSQL (Metastore backend)
tribench sys setup postgresql
tribench sys start postgresql

# 2. Setup MinIO (Object storage)
tribench sys setup minio
tribench sys start minio

# 3. Setup Hive Metastore (Iceberg catalog)
tribench sys setup hive-metastore
tribench sys start hive-metastore

# 4. Setup Trino (automatically configures Iceberg catalog)
tribench sys setup trino
tribench sys start trino

# Verify all systems are running
tribench sys status postgresql
tribench sys status minio
tribench sys status hive-metastore
tribench sys status trino
```

### Loading Data into Iceberg

```bash
# Generate TPC-H dataset in Parquet format (if not already generated)
tribench data generate tpch-sf0.01 --format parquet

# Load into Iceberg tables
tribench data load-iceberg tpch-tiny \
  --catalog iceberg \
  --schema tpch \
  --no-partition \
  --validate

# Options:
#   --catalog: Iceberg catalog name (default: iceberg)
#   --schema: Schema/database name (default: tpch)
#   --storage: Custom S3 location (optional)
#   --partition: Enable partitioning for large tables (default: true)
#   --no-partition: Disable partitioning (recommended for small datasets)
#   --validate: Validate tables after loading
```

### Viewing Iceberg Metadata

```bash
# List all datasets (shows both Parquet and Iceberg)
tribench data list

# View Iceberg dataset metadata
tribench data info tpch-tiny-iceberg

# Output includes:
#   - Catalog and schema information
#   - Iceberg format version (v1 or v2)
#   - Snapshot IDs and timestamps for each table
#   - Manifest file counts
#   - Storage location
#   - Row counts per table

# View detailed metadata
tribench data info tpch-tiny-iceberg --detailed
```

### Validating Iceberg Tables

```bash
# Validate all tables for a scale factor
tribench data validate-iceberg --scale-factor tiny

# Validate specific tables
tribench data validate-iceberg \
  --scale-factor 1 \
  --tables customer,orders,lineitem \
  --detailed

# Validation checks:
#   - Table existence in catalog
#   - Row count accuracy
#   - Schema integrity
#   - Iceberg metadata (snapshots, data files)
```

### Iceberg Features Supported

- ✅ **Table Creation**: Automatic schema inference from Parquet
- ✅ **Data Loading**: Batch inserts with configurable batch size
- ✅ **Partitioning**: Optional partitioning for large tables
- ✅ **Snapshots**: Automatic snapshot creation and tracking
- ✅ **Metadata Tracking**: Registry-based persistence of Iceberg metadata
- ✅ **Validation**: Comprehensive table and metadata validation
- ✅ **Format Versions**: Support for Iceberg v1 and v2 tables
- ✅ **Storage**: S3-compatible storage via MinIO

### Iceberg Dataset Registry

Iceberg datasets are registered with comprehensive metadata:

```yaml
# Example: datasets/registry.yaml
tpch-tiny-iceberg:
  name: tpch-tiny-iceberg
  format: iceberg
  benchmark_type: tpch
  scale_factor: 0.01
  location: iceberg.tpch
  iceberg_catalog: iceberg
  iceberg_schema: tpch
  format_version: 2
  snapshot_ids:
    customer: 5597780913108285715
    lineitem: 4233068895913014946
    # ... other tables
  snapshot_timestamps:
    customer: '2025-10-30 22:01:20.730000+00:00'
    lineitem: '2025-10-30 22:04:25.263000+00:00'
    # ... other tables
  properties:
    source_dataset: tpch-tiny
    partitioned: false
    storage_location: default
```

### Future Iceberg Features

Planned enhancements for upcoming releases:

- 🔄 **Time Travel**: Query historical snapshots
- 🔄 **Schema Evolution**: Track and test schema changes
- 🔄 **Partition Evolution**: Test partition strategy changes
- 🔄 **Compaction**: Optimize file layouts
- 🔄 **Metadata Refresh**: Update registry with current snapshot state
- 🔄 **Snapshot Comparison**: Diff between snapshots

## Development Status

This framework is currently under development as part of a dissertation project on benchmarking SQL workloads on distributed data lakehouses.

## License

Apache License 2.0
