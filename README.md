# TriBench: A Framework for Benchmarking SQL Workloads on Distributed Data Lakehouses

**L4 Honours Dissertation** — University of Glasgow, 2026
**Author:** Lin Yuan (2736414Y)

## Abstract

Benchmarking distributed SQL systems is significantly harder than benchmarking traditional databases. A modern data lakehouse deployment relies on several coordinated services that must all be configured, started, and monitored together. Existing tools for Apache Trino either assume the cluster is already running, lack hardware monitoring, or embed environment-specific assumptions that prevent experiments from being reproduced on different machines.

TriBench addresses this gap as a cross-platform benchmarking framework for distributed data lakehouses. Experiments are defined declaratively and run unchanged across a local single-machine deployment or a multi-node cloud cluster by switching a single configuration file. Hardware and resource metrics are collected automatically alongside query execution, and all results are packaged into a self-contained, portable bundle that can be shared and reproduced without additional setup.

## Evaluation

TriBench was evaluated across three environments of increasing scale:

- **Local Docker** — single-node deployment on an Apple M4 Pro, TPC-H SF1
- **On-premises Kubernetes** — University of Glasgow GPG cluster (2 workers), TPC-DS SF10 and a custom dataset
- **Google Kubernetes Engine** — 1/2/4 worker scaling study and full suite run at SF100

In all three environments, the same experiment definition ran without modification. Monitoring overhead remained below 5% across all environments. The SF100 suite ran unattended for 7.7 hours on GKE, producing reproducible results throughout.

## Repository Structure

```
bundles/        — self-contained evaluation bundles (docker, gpg, gcp-1w/2w/4w)
config/         — HOCON configuration and host profiles
experiments/    — experiment YAML definitions
queries/        — TPC-H and TPC-DS SQL query files
lib/tribench/   — framework source code
systems/        — Docker Compose and Kubernetes manifests
docs/diss/      — dissertation LaTeX source
```

For installation and usage, see [manual.md](manual.md).

## License

Apache License 2.0
