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

| Group | Commands | Purpose |
|---|---|---|
| `bundle` | `create` `set` `archive` | Create, activate, and package bundles |
| `sys` | `start` `stop` `setup` `teardown` `status` | Manage the lakehouse stack |
| `data` | `generate` `load` `list` `info` | Generate and load datasets into Iceberg |
| `exp` | `run` | Execute a single experiment |
| `suite` | `run` `list` `show` | Run grouped experiment suites |
| `result` | `show` `list` `export` `analyze` `delete` | Inspect and export results |
| `config` | `profile` `show` `trace` | Switch profiles and inspect resolved config |

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
