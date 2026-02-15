# TPC-DS Experiment Suite

Collection of TPC-DS benchmark experiments for TriBench.

## Available Experiments

### Development & Testing

- **tpcds-dev.yaml** - Quick validation (4 simple queries, no monitoring)
  - Use for: Smoke testing, development
  - Runs: 1, Timeout: 300s
  - Queries: q03, q07, q52, q55

### Standard Benchmarks

- **tpcds-sf1.yaml** - Complete SF1 benchmark (10 queries with monitoring)
  - Use for: Local benchmarking, baseline measurements
  - Runs: 3, Timeout: 600s
  - Includes: System monitoring, result storage
  - Queries: q01, q03, q07, q19, q27, q42, q52, q55, q73, q96

### Cloud Deployments

- **tpcds-gcp.yaml** - GKE deployment with Kubernetes monitoring
  - Use for: Distributed workloads, pod-level metrics
  - Runs: 3, Timeout: 600s
  - Monitoring: System + Kubernetes pod metrics
  - Queries: Same as tpcds-sf1.yaml

## Usage

### Quick Test
```bash
tribench exp run experiments/tpcds-dev.yaml
```

### Standard Benchmark
```bash
tribench exp run experiments/tpcds-sf1.yaml
```

### Cloud Deployment
```bash
# Ensure GKE cluster is running and port-forwarding is active
tribench exp run experiments/tpcds-gcp.yaml
```

## Query Coverage

Current experiments include a representative subset of TPC-DS queries:

| Query | Category          | Complexity | Tables | Description |
|-------|-------------------|------------|--------|-------------|
| q01   | Reporting         | High       | 4      | Customer return analysis |
| q03   | Reporting         | Low        | 3      | Brand sales by year |
| q07   | Reporting         | Medium     | 5      | Promotional sales |
| q19   | Ad-hoc            | High       | 6      | Multi-channel brand sales |
| q27   | Iterative OLAP    | High       | 5      | ROLLUP aggregations |
| q42   | Reporting         | Low        | 3      | Category sales |
| q52   | Reporting         | Low        | 3      | Brand sales |
| q55   | Reporting         | Low        | 3      | Manager brand sales |
| q73   | Iterative OLAP    | Very High  | 4      | Customer patterns |
| q96   | Ad-hoc            | Medium     | 4      | Time-based analysis |

## Creating Custom Experiments

### Add More Queries

```yaml
name: "tpcds-custom"
description: "Custom TPC-DS subset"
system: "trino"
connection:
  catalog: "iceberg"
  schema: "tpcds"
runs: 3
query_files:
  - "apps/tpcds/queries/q01.sql"
  - "apps/tpcds/queries/q02.sql"
  # Add your query selection
```

### Adjust Scale Factor

For larger datasets, update connection schema:

```yaml
connection:
  schema: "tpcds_sf10"  # For 10GB dataset
  # or
  schema: "tpcds_sf100"  # For 100GB dataset
```

### Enable Parallel Execution

```yaml
parallel_queries: 4  # Run 4 queries concurrently
```

### Add Validation Rules

```yaml
validation:
  min_success_rate: 0.95
  max_execution_time_variance: 0.3
```

## Performance Expectations

### Scale Factor 1 (1GB)

**Simple Queries** (q03, q07, q52, q55):
- Execution Time: 1-5 seconds
- Memory: < 1GB

**Medium Queries** (q19, q42, q96):
- Execution Time: 5-15 seconds
- Memory: 1-2GB

**Complex Queries** (q01, q27, q73):
- Execution Time: 15-60 seconds
- Memory: 2-4GB

**Note**: Times vary based on:
- Hardware configuration
- Trino worker count
- Data partitioning
- Cache warmth

## Monitoring

Experiments collect:
- **Query metrics**: Execution time, rows processed, data scanned
- **System metrics**: CPU, memory, network, disk I/O
- **Kubernetes metrics** (GCP): Pod CPU/memory, node utilization

View results:
```bash
# Summary
tribench res summary <experiment_id>

# Detailed metrics
tribench res monitoring <experiment_id> --run <run_number>

# Export to CSV
tribench res export <experiment_id> results.csv
```

## Troubleshooting

### Query Timeouts

Increase timeout for complex queries:
```yaml
timeout_seconds: 1200  # 20 minutes
```

### Memory Issues

- Reduce `parallel_queries` to 1
- Increase Trino `query.max-memory-per-node`
- Use smaller scale factor for testing

### Connection Errors

Ensure:
- Trino is running: `tribench sys status`
- Port forwarding active (Kubernetes): `kubectl port-forward`
- Correct schema name in connection config

## Next Steps

1. **Generate more queries**: See `apps/tpcds/queries/README.md`
2. **Scale up**: Generate larger datasets with `generate_tpcds.sh`
3. **Compare engines**: Run same queries on different systems
4. **Optimize**: Tune partitioning, caching, and query plans

## References

- Query details: `apps/tpcds/queries/README.md`
- Schema: `lib/tribench/data/dataset/schema.py`
- Data generation: `utils/generate_tpcds.sh`
- TPC-DS Spec: http://www.tpc.org/tpcds/
