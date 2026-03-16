# Evaluation Plan — TriBench Dissertation (Ch7)

## Structure Overview

```
§7.1  Experimental Setup
§7.2  Framework Overhead (Experiment 0)
§7.3  Level 1 — Local Docker Baseline                    (Scenario 1 / Jordan)
§7.4  Level 2 — Bare-Metal Kubernetes, Custom Workloads  (Scenario 2 / Alex + Taylor)
§7.5  Level 3 — GKE Worker Scaling + Full Suite          (Scenario 3 / Sam)
§7.6  Requirements Coverage Summary
```

---

## §7.1 Experimental Setup

### Local Environment (Level 1)
- **Bundle**: `tpch-docker` — created with `tribench bundle create tpch-docker`
- **Hardware**: MacBook M4, 24 GB unified memory, NVMe SSD, macOS Sequoia
- **Runtime**: Docker Desktop, Trino 434
- **Profile**: `docker.conf` — backend=docker, coordinator heap 4 GB
- **Dataset**: TPC-H SF 1 (~320 MB Parquet in MinIO)
- **Stack**: Trino + Hive Metastore + MinIO + PostgreSQL, started via `tribench sys start`

### Bare-Metal Kubernetes Environment (Level 2)
- **Bundle**: `tpcds-gpg` — created with `tribench bundle create tpcds-gpg`
- **Hardware**: GPG cluster (University of Glasgow bare-metal nodes)
- **Storage**: Ceph block device via Rook operator
- **Metrics**: Kubernetes Metrics Server (enables S2 per-pod collection)
- **Profile**: `gpg-multinode.conf` — backend=kubernetes, coordinator heap 16 GB, 2 workers
- **Connectivity**: automatic `kubectl port-forward` to localhost:8080
- **Datasets**: TPC-DS SF 10 + custom domain dataset (registered in bundle registry)

### GCP GKE Environment (Level 3)
- **Bundle**: `gke-suite` — created with `tribench bundle create gke-suite`
- **Cluster**: GKE, worker count swept across 4 → 8 workers
- **Profile**: `gcp-gke.conf` (workers list changed per run; all else fixed)
- **Metrics**: GKE built-in Metrics Server
- **Datasets**: TPC-H SF 100, TPC-DS SF 100, ecommerce-tiny custom dataset (3 total)

---

## §7.2 Framework Overhead (Experiment 0)

**Goal**: Quantify instrumentation cost across all three deployment backends; evidence for S4 (<5% overhead) and M19 (reproducibility). Measuring on all three environments is important because the Kubernetes backends incur additional overhead from per-pod Metrics Server polling (S2) that does not exist in Docker.

**Dataset**: TPC-H SF 0.01 used for all environments (small scale keeps runs fast and makes timing noise negligible).

**Queries**: Q1 (scan-heavy), Q6 (filter-only, light), Q18 (aggregation + join, medium).

**Three run types per environment**:
| Run | Description |
|-----|-------------|
| A   | TriBench — all monitoring enabled (host metrics + Trino REST stats + per-pod metrics where applicable) |
| B   | TriBench — monitoring disabled (`monitoring.enabled = false`) |
| C   | Raw `trino-cli` via port-forward — no framework at all, manual timing |

**Repetitions**: 5 measured runs per query per run type (1 warmup discarded).

**Metric**: overhead = `(mean_A − mean_C) / mean_C × 100%`

### Environments
| Environment | Profile | Extra overhead source vs Docker |
|-------------|---------|--------------------------------|
| Local Docker | `docker.conf` | baseline |
| GPG K8s | `gpg-multinode.conf` (2 workers) | per-pod Metrics Server API calls |
| GKE | `gcp-gke.conf` (4 workers) | per-pod Metrics Server API calls + network latency |

For K8s run C: port-forward is established manually (`kubectl port-forward`) and `trino-cli` is invoked directly; timing recorded with `time`.

### Evidence to collect
- Overhead table: mean latency ± std dev for A / B / C, per query, per environment (3×3×3 cells)
- Cross-environment overhead summary: single row per environment showing mean overhead % across the three queries
- Variance table: coefficient of variation across 5 runs per configuration (confirms M19 <5% variance claim)

### Figures planned
- **Fig 7.7**: Grouped bar chart — overhead % (run A vs C) for Q1 / Q6 / Q18 across Docker / GPG / GKE

**Requirements closed**: S4, M19

---

## §7.3 Level 1 — Local Docker Baseline (~10 min)

**Corresponds to**: Scenario 1 (Jordan)

### Experiment config
| Parameter | Value |
|-----------|-------|
| Bundle | `tpch-docker` |
| Profile | `docker.conf` (Docker, 2 workers, 4 GB heap) |
| Dataset | TPC-H SF 1 |
| Queries | All 22 TPC-H queries |
| Warmup | 1 run discarded |
| Measured runs | 3 |
| Timeout | 60 s per query |

### Timing estimate
| Step | Time |
|------|------|
| `tribench sys start` | ~1 min |
| `tribench data load` | ~1 min |
| 22 queries × 3 runs × ~5 s avg | ~5.5 min |
| `tribench sys stop` | ~30 s |
| **Total** | **~8 min** |

### Evidence to collect
- Terminal output of `tribench exp run` showing stack start → query execution → teardown
- `tribench result show` output listing all 22 queries with per-query latency + bytes scanned
- Exported CSV (`tribench result export --format csv`)
- Host metric time-series plot: CPU/memory over experiment duration with query-start markers
- Bundle archive: `tribench bundle archive` producing `.tar.gz`

### Figures planned
- **Fig 7.1**: Bar chart — wall-clock time for all 22 TPC-H queries (Q1–Q22 on x-axis)
- **Fig 7.2**: Time-series — CPU % and memory GB during experiment with query boundaries marked

### Requirements closed
M1, M2, M5, M6, M7, M8, M9, M10, M11, M15, M16, M17, M18, M19, M20, M21

---

## §7.4 Level 2 — Bare-Metal Kubernetes, Custom Workloads (~1 hr)

**Corresponds to**: Scenario 2 (Alex + Taylor)

Level 2 demonstrates the Kubernetes backend, per-pod monitoring, and custom dataset support on the GPG cluster at a fixed 2-worker configuration. Worker scaling is deferred to Level 3 (GKE) where elastic node provisioning makes sweep experiments practical.

**Bundle**: `tpcds-gpg` — created with `tribench bundle create tpcds-gpg`, shared between Alex and Taylor.

### Experiments
| Experiment | Queries | Dataset | Profile | Runs |
|------------|---------|---------|---------|------|
| `tpcds-gpg.yaml` | TPC-DS Q3, Q7, Q13, Q19, Q27, Q34, Q42, Q52, Q65, Q82 (10 queries) | TPC-DS SF 10 | `gpg-multinode.conf` (2 workers) | 1 warmup + 5 measured |
| `custom-gpg.yaml` | 3 custom e-commerce analytical queries | ecommerce-tiny | `gpg-multinode.conf` (2 workers) | 1 warmup + 3 measured |

### Timing estimate
| Step | Time |
|------|------|
| K8s stack start | ~5 min |
| TPC-DS SF 10 dataset load | ~15 min |
| 10 queries × 5 runs × ~25 s avg | ~21 min |
| Custom queries × 3 runs | ~5 min |
| Teardown | ~3 min |
| **Total** | **~50 min** |

### Evidence to collect
- Bar chart of TPC-DS query latencies (all 10 queries, mean ± std dev)
- Per-pod CPU metric plot: coordinator vs worker-1 vs worker-2 during Q13 (join-heavy)
- `tribench config trace backend` confirming profile layer resolved correctly
- Custom dataset registry YAML snippet (demonstrates M3/M4)
- Cross-run result CSV showing 5 runs accumulating under separate run IDs (M10)

### Figures planned
- **Fig 7.3**: Bar chart — TPC-DS query latencies on GPG (mean ± std dev, all 10 queries)
- **Fig 7.4**: Stacked area chart — per-pod CPU (millicores) over time during a join-heavy query

### Requirements closed
M3, M4, M12, M13, M14, S2

---

## §7.5 Level 3 — Cloud Suite Execution (~2.5–3 hrs)

**Corresponds to**: Scenario 3 (Sam)

### Suite composition (single `tribench suite run`)
| # | Experiment | Dataset | Queries |
|---|------------|---------|---------|
| 1 | `tpch-all.yaml` | TPC-H SF 100 | All 22 TPC-H queries |
| 2 | `tpcds-selected.yaml` | TPC-DS SF 100 | 10 representative TPC-DS queries |
| 3 | `custom-ecommerce.yaml` | ecommerce-tiny | 3 custom e-commerce queries |

**Profile**: `gcp-gke.conf` (8 workers)  
**Warmup**: 1 run per experiment  
**Measured**: 3 runs per experiment

### Timing estimate
| Step | Time |
|------|------|
| GKE stack provision + start | ~20 min |
| Dataset loads (TPC-H SF100, TPC-DS SF100, ecommerce-tiny) | ~30 min |
| Experiments 1–3 (suite, auto lifecycle) | ~75 min |
| Teardown | ~5 min |
| **Total** | **~2.5 hrs** |

### Evidence to collect
- Suite execution log: showing automatic start/stop transitions between experiments
- Cross-level portability table: TPC-H at Level 1 (Docker, SF1) vs Level 3 (GKE 8w, SF100)
- GKE per-pod metric plots: 8-worker resource distribution during TPC-DS heavy query
- `tribench result export` producing full result CSV (appendix material)
- Bundle reproduction: colleague activates archived bundle and runs `tribench suite run` to match results

### Figures planned
- **Fig 7.5**: Worker scaling line chart — TPC-H Q9/Q18/Q21 latency vs 4w / 8w (GKE)
- **Fig 7.6**: Suite execution timeline — Gantt-style showing 3 experiments with stack start/stop markers

### Requirements closed
S1, M13 (cross-env confirmed at cloud scale), M18 (archive + reproduction)

---

## §7.6 Requirements Coverage Summary

A single table mapping every MoSCoW requirement to the section providing primary evidence.

| Requirement | Description | Primary evidence |
|-------------|-------------|-----------------|
| M1 | Declarative YAML | §7.3 Level 1 |
| M2 | TPC-H suite | §7.3 Level 1 |
| M3 | User datasets | §7.4 Level 2 |
| M4 | Unified query spec | §7.4 Level 2 |
| M5 | Execution control | §7.3 Level 1 |
| M6 | Host telemetry | §7.3 Level 1 |
| M7 | Per-query stats | §7.3 Level 1 |
| M8 | Relational schema | §7.3 Level 1 |
| M9 | Export formats | §7.3 Level 1 |
| M10 | Non-overwriting runs | §7.4 Level 2 |
| M11 | Docker lifecycle | §7.3 Level 1 |
| M12 | Kubernetes lifecycle | §7.4 Level 2 |
| M13 | Cross-backend portability | §7.4 Level 2, §7.5 Level 3 |
| M14 | Named profiles | §7.4 Level 2 |
| M15 | Bundle structure | §7.3 Level 1 |
| M16 | Bundle creation | §7.3 Level 1 |
| M17 | Bundle activation | §7.3 Level 1 |
| M18 | Bundle archiving + reproduction | §7.5 Level 3 |
| M19 | Reproducibility (<5% variance) | §7.2 Overhead |
| M20 | Platform portability | §7.3 Level 1 (macOS) |
| M21 | Observability / logs | §7.3 Level 1 |
| S1 | Suite abstraction | §7.5 Level 3 |
| S2 | Per-pod K8s metrics | §7.4 Level 2 |
| S4 | Low monitoring overhead | §7.2 Overhead |

---

## Figures Summary

| Figure | Type | Section | Purpose |
|--------|------|---------|---------|
| 7.1 | Bar chart | §7.3 | TPC-H 22-query wall-clock times (Docker, SF1) |
| 7.2 | Time-series | §7.3 | CPU + memory during Level 1 experiment |
| 7.3 | Bar chart | §7.4 | TPC-DS query latencies on GPG (mean ± std dev, SF10) |
| 7.4 | Stacked area | §7.4 | Per-pod CPU during join-heavy TPC-DS query (GPG) |
| 7.5 | Line chart | §7.5 | Worker scaling: TPC-H Q9/Q18/Q21 latency vs 4w/8w (GKE) |
| 7.6 | Gantt / timeline | §7.5 | Suite execution timeline (GKE, 3 experiments) |
| 7.7 | Table | §7.2 | TriBench vs uninstrumented latency (overhead) |
