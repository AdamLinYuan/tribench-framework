# TPC-H Demo Experiments

This directory contains demo experiments showcasing different TPC-H query patterns and TriBench framework capabilities.

## Experiments

| Experiment | Queries | Focus | Est. Time |
|------------|---------|-------|-----------|
| `tpch-quick-smoke.yaml` | Inline simple queries | System validation | < 1 min |
| `tpch-aggregation-demo.yaml` | Q1, Q6 | GROUP BY, SUM, aggregation | ~2-3 min |
| `tpch-join-demo.yaml` | Q3, Q5, Q10 | Multi-table joins (3-6 tables) | ~3-4 min |
| `tpch-subquery-demo.yaml` | Q4, Q11, Q22 | EXISTS, IN, correlated subqueries | ~3-4 min |
| `tpch-analytical-demo.yaml` | Q7, Q8, Q9 | Complex business analytics | ~4-5 min |
| `tpch-top5-benchmark.yaml` | Q1, Q3, Q5, Q6, Q14 | Representative benchmark | ~5-7 min |

## Quick Start

### Run a Single Experiment

```bash
# Smoke test (validates connectivity)
tribench exp run experiments/demo/tpch-quick-smoke.yaml

# Aggregation queries
tribench exp run experiments/demo/tpch-aggregation-demo.yaml

# Top 5 representative benchmark
tribench exp run experiments/demo/tpch-top5-benchmark.yaml
```

### Run the Complete Demo Suite

```bash
# Run all experiments in sequence
tribench suite run experiments/suites/tpch-demo-suite.yaml
```

## Query Patterns Covered

### Aggregation (Q1, Q6)
- **Q1 - Pricing Summary Report**: Heavy aggregation with GROUP BY on multiple columns
- **Q6 - Forecasting Revenue Change**: Simple scan with aggregation

### Joins (Q3, Q5, Q10)
- **Q3 - Shipping Priority**: 3-way join (lineitem, orders, customer)
- **Q5 - Local Supplier Volume**: 6-way join (most tables)
- **Q10 - Returned Item Reporting**: 4-way join with filtering

### Subqueries (Q4, Q11, Q22)
- **Q4 - Order Priority Checking**: EXISTS subquery
- **Q11 - Important Stock Identification**: Correlated subquery with HAVING
- **Q22 - Global Sales Opportunity**: Complex nested subqueries

### Analytical (Q7, Q8, Q9)
- **Q7 - Volume Shipping**: Multi-year shipping analysis between nations
- **Q8 - National Market Share**: Market share calculation with CASE
- **Q9 - Product Type Profit Measure**: Profit analysis with complex joins

### Top 5 Representative (Q1, Q3, Q5, Q6, Q14)
- Covers aggregation, joins, scans, and conditional logic
- Most commonly used for benchmarking comparisons

## Prerequisites

1. **Kubernetes deployment running**:
   ```bash
   tribench sys deploy
   ```

2. **Iceberg data loaded**:
   ```bash
   tribench data load-iceberg --dataset tpch-sf0_01
   ```

3. **Port forwarding active** (auto-managed or manual):
   ```bash
   tribench sys port-forward status
   # If needed: tribench sys port-forward start
   ```

## Results

Results are saved to `results/` directory with:
- JSON raw results
- Markdown summary reports
- Performance metrics and statistics

View results:
```bash
tribench res list
tribench res show <experiment-name>
```

## Customization

Each experiment can be customized by:
1. Editing the YAML file directly
2. Using overrides in a suite definition
3. Passing CLI flags

Example override in suite:
```yaml
experiments:
  - name: "custom-aggregation"
    path: "experiments/demo/tpch-aggregation-demo.yaml"
    overrides:
      runs: 10
      warmup_runs: 3
      timeout_seconds: 300
```
