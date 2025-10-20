# TPC-H Benchmark Queries

This directory contains the official TPC-H benchmark queries implemented for TriBench.

## Overview

The TPC-H benchmark consists of 22 decision support queries designed to exercise various aspects of database system capabilities. These queries simulate real-world analytics workloads on a wholesale supplier database.

## Query Characteristics

| Query | Name | Type | Complexity | Key Features |
|-------|------|------|------------|--------------|
| Q1 | Pricing Summary Report | Aggregation | Simple | GROUP BY, aggregates, date filter |
| Q3 | Shipping Priority | Join + Aggregation | Medium | 3-way join, ORDER BY, LIMIT |
| Q6 | Forecasting Revenue Change | Aggregation | Simple | Single table, multiple filters |
| Q12 | Shipping Modes | Join + Aggregation | Medium | CASE expressions, date ranges |
| Q14 | Promotion Effect | Join + Aggregation | Medium | Pattern matching (LIKE), percentage |
| Q19 | Discounted Revenue | Join + Complex Filter | High | Multiple OR conditions, complex predicates |

## Query Files

Each query is stored in a separate `.sql` file:
- `q01.sql` - Pricing Summary Report Query
- `q03.sql` - Shipping Priority Query
- `q06.sql` - Forecasting Revenue Change Query
- `q12.sql` - Shipping Modes and Order Priority Query
- `q14.sql` - Promotion Effect Query
- `q19.sql` - Discounted Revenue Query

## Usage in Experiments

Reference these queries from your experiment configurations:

```yaml
# experiments/tpch-q1-memory-sf1.yaml
name: "tpch-q1-memory-sf1"
query_file: "apps/tpch/queries/q01.sql"
connection:
  catalog: "memory"
  schema: "tpch_sf1"
```

## Query Selection Rationale

These 6 queries were selected to provide:
1. **Variety of patterns**: Simple aggregations, complex joins, filtering
2. **Performance diversity**: Fast queries (Q6) vs. complex queries (Q19)
3. **Partition sensitivity**: Queries that benefit from partitioning (Q1, Q6) vs. join-heavy queries (Q3, Q12)
4. **Scalability testing**: Queries that scale differently with data size

## TPC-H Specification

These queries are based on the official TPC-H Benchmark Specification v2.18.0:
http://www.tpc.org/tpc_documents_current_versions/pdf/tpc-h_v2.18.0.pdf

## Expected Results

All queries have been validated against Trino's built-in TPC-H catalog:
- **Q1**: Returns 4 rows (returnflag × linestatus combinations)
- **Q3**: Returns 10 rows (LIMIT 10)
- **Q6**: Returns 1 row (single aggregate)
- **Q12**: Returns 2 rows (MAIL, SHIP)
- **Q14**: Returns 1 row (percentage)
- **Q19**: Returns 1 row (single revenue value)

## Adding More Queries

To add additional TPC-H queries (Q2, Q4, Q5, etc.):

1. Create new file: `apps/tpch/queries/qXX.sql`
2. Add query with documentation header
3. Validate against built-in TPC-H catalog
4. Update this README with query characteristics
5. Create corresponding experiment configurations

## Performance Considerations

- **Q1, Q6**: Pure aggregation, benefit from columnar formats and partition pruning
- **Q3, Q12**: Join-heavy, benefit from proper join strategies and statistics
- **Q14, Q19**: Require part table joins, test predicate pushdown effectiveness

## Testing

Validate queries against Trino's built-in TPC-H catalog:

```bash
# Test Q1 on tiny dataset
tribench exp run test-tpch-q1-tiny --catalog tpch --schema tiny
```

## References

- TPC-H Specification: http://www.tpc.org/tpch/
- Trino TPC-H Connector: https://trino.io/docs/current/connector/tpch.html
- Query Explanations: http://www.tpc.org/tpc_documents_current_versions/pdf/tpc-h_v2.18.0.pdf (Appendix A)
