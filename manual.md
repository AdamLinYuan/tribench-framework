# TriBench

A cross-platform benchmarking framework for SQL workloads on distributed data lakehouses using Apache Trino and Apache Iceberg.

## Overview

TriBench manages the full lifecycle of a Trino lakehouse benchmark: provisioning the stack, loading data, executing queries, collecting hardware telemetry, and storing results — all from a single declarative experiment definition. The same definition runs unchanged on a local Docker deployment or a multi-node Kubernetes cluster by switching a single configuration profile.

**Stack:** Trino 434 · Apache Iceberg · Hive Metastore 4.0.0 · MinIO · PostgreSQL 15

**Backends:** Docker Compose (single-node) · Kubernetes (local KinD, bare-metal, GKE)

**Built-in benchmarks:** TPC-H (22 queries) · TPC-DS (99 queries) · custom Parquet datasets

## Prerequisites

- [Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Docker Desktop (Docker backend)
- MinIO Client (`mc`) — for object storage operations
- `kubectl` (Kubernetes backend)
- `gcloud` CLI (GKE only)

## Installation

```bash
conda env create -f environment.yml
conda activate tribench
pip install -e .
tribench --version
```

## Quick Start

```bash
# 1. Create and activate a bundle
tribench bundle create my-benchmark
tribench bundle set my-benchmark

# 2. Start the lakehouse stack (Docker)
tribench config profile docker
tribench sys start all

# 3. Generate and load a dataset (TPC-DS requires generation; TPC-H loads directly)
tribench data generate tpcds-sf1 --format parquet
tribench data load tpch-sf1 --schema tpch_sf1

# For custom datasets: place Parquet files inside a named folder under datasets/
# (either inside the active bundle or the framework root), then run:
tribench data load my_dataset --schema my_schema

# 4. Run an experiment
tribench exp run experiments/tpch-all.yaml

# 5. View results
tribench res show
tribench res export --format csv
```

## Configuration

Parameters are resolved through four layers, each overriding the one below:

| Layer | File | Purpose |
|---|---|---|
| 1 | `config/reference.conf` | Framework defaults — do not edit |
| 2 | `config/hosts/<profile>.conf` | Machine-specific settings (backend, heap, cluster address) |
| 3 | `experiments/<name>.yaml` | Workload settings (runs, timeout, queries) |
| 4 | CLI flags / env vars | Per-run overrides |

Switch deployment environment by changing the active profile. TriBench ships with example profiles in `config/hosts/` that can be used as-is or adapted as a starting point for your own environment:

```bash
tribench config profile set docker          # local Docker Compose
tribench config profile set gpg-multinode   # bare-metal Kubernetes
tribench config profile set gcp-gke-4w      # GKE, 4 workers
```

## Bundles

A bundle packages all experiment artefacts into a portable, self-contained directory:

```
my-benchmark/
├── bundle.yaml
├── config/hosts/       # deployment profiles
├── experiments/        # experiment YAML files
├── apps/               # SQL query files
├── datasets/           # dataset registry and files
├── log/                # execution logs
└── results/
    └── tribench.db     # SQLite result database
```

All bundles used in the dissertation evaluation (`docker`, `gpg`, `gcp-1w`, `gcp-2w`, `gcp-4w`) are included in `bundles/`. The full datasets were removed from the repository due to size constraints. Small reference datasets (TPC-H SF0.01, TPC-DS SF0.01, and the custom e-commerce dataset) are included in `datasets/` and can be used to verify the setup.

To reproduce an evaluation bundle, activate it and generate the datasets referenced by its experiments:

```bash
tribench bundle set docker          # or gpg, gcp-4w, etc.
tribench data generate tpch-sf1 --schema tpch_sf1
tribench data generate tpcds-sf10 --schema tpcds_sf10
```

## CLI Reference

### bundle — Bundle management

| Command | Description |
|---|---|
| `archive` | Archive the bundle's results and logs |
| `clear` | Clear the active bundle state |
| `create` | Scaffold a new bundle directory |
| `info` | Show bundle metadata and resolved paths |
| `list` | List all experiment YAML files in the bundle |
| `set` | Set a bundle as active persistently |
| `show` | Show the currently active bundle |
| `validate` | Check that the bundle has all required elements |

### sys — System lifecycle management

| Command | Description |
|---|---|
| `cluster` | Manage the Kind Kubernetes cluster |
| `logs` | Show system component logs |
| `port-forward` | Manage Kubernetes port forwarding tunnels |
| `setup` | Set up the lakehouse system components |
| `start` | Start the system and poll for readiness |
| `status` | Check current system status |
| `stop` | Stop the system gracefully |
| `teardown` | Tear down the system (destructive) |

### exp — Experiment execution

| Command | Description |
|---|---|
| `cancel` | Cancel a currently running experiment |
| `config` | Show the configuration for a specific experiment |
| `list` | List available experiments |
| `run` | Execute an experiment end-to-end |
| `status` | Check the status of a running experiment |

### res — Results and analysis

| Command | Description |
|---|---|
| `analyze` | Analyze results (statistics, performance, scalability, compare, regression) |
| `archive` | Archive old experiment results |
| `delete` | Delete an experiment result by ID |
| `export` | Export results to CSV, JSON, or Parquet |
| `list` | List all recorded experiment results |
| `monitoring` | Show hardware monitoring telemetry for an experiment |
| `queries` | Show detailed per-query execution data |
| `reset-db` | Reset the SQLite database by deleting all runs |
| `show` | Show high-level summary of an experiment result |
| `suite-summary` | Show an aggregated summary across a suite of runs |
| `summary` | Generate comparison summary for experiments |

### data — Dataset management

| Command | Description |
|---|---|
| `generate` | Generate a benchmark dataset (TPC-H or TPC-DS) |
| `info` | Show detailed dataset information including snapshot IDs |
| `list` | List available datasets |
| `load` | Load a dataset into the deployed Iceberg catalogue |
| `validate` | Validate dataset integrity |
| `validate-iceberg` | Validate Iceberg tables in the catalogue |

### config — Configuration management

| Command | Description |
|---|---|
| `defaults` | Show framework defaults |
| `profile` | Manage the active configuration profile |
| `show` | Show the current merged configuration |
| `trace` | Trace where a specific configuration value originated |
| `validate` | Validate the complete configuration for errors |

### suite — Experiment suite execution

| Command | Description |
|---|---|
| `list` | List available experiment suites |
| `run` | Execute all experiments in a suite |
| `show` | Show detailed information about a suite |

### Experiment definition

```yaml
name: "tpch-sf1"
system: "trino"
connection:
  host: "localhost"
  port: 8080
  catalog: "iceberg"
  schema: "tpch_sf1"
runs: 3
warmup_runs: 1
timeout_seconds: 60
monitoring:
  enabled: true
  interval_seconds: 2.0
query_files:
  - "queries/tpch/queries/q01.sql"
validation:
  min_success_rate: 0.95
```

### Analysis commands

```bash
tribench res analyze statistics  <run-id>              # mean, median, P95, P99 per query
tribench res analyze performance <run-id>              # throughput and per-query breakdown
tribench res analyze compare     <run-id-a> <run-id-b> # t-test comparison between two runs
tribench res analyze scalability <run-id-a> <run-id-b> # speed-up and parallel efficiency
tribench res analyze regression  <run-id-a> <run-id-b> # regression detection with severity
```

## Kubernetes Deployment

For step-by-step deployment guides see:

- [GPG bare-metal cluster](docs/GPG/GPG_DEPLOYMENT.md)
- [Google Kubernetes Engine (GKE)](docs/GKE/GCP_DEPLOYMENT.md)

## Testing

```bash
pytest                  # run all 267 unit tests
pytest --cov=lib/       # with coverage report
```

## License

Apache License 2.0
