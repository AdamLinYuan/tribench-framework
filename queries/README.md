# Apps Directory

This directory contains benchmark applications and SQL workloads that can be referenced from experiment configurations.

## Purpose

The apps directory provides a **single source of truth** for benchmark queries, separating query definitions from experiment configurations. This approach:
- ✅ Eliminates query duplication across experiments
- ✅ Makes queries easier to maintain and verify
- ✅ Enables reusability across different systems and configurations
- ✅ Provides clear version control for query changes

## Structure

```
apps/
└── tpch/                   # TPC-H benchmark queries
    ├── queries/            # Individual SQL query files (q01.sql - q22.sql)
    └── README.md           # TPC-H documentation
```

## Current Status

**Implemented:**
- ✅ TPC-H queries: Q1, Q3, Q6, Q12, Q14, Q19 (6 core queries for dissertation)

**Future (Optional):**
- Additional TPC-H queries (Q2, Q4, Q5, Q7-Q11, Q13, Q15-Q18, Q20-Q22)
- TPC-DS benchmark queries (if scope expands)
- Custom microbenchmark queries

## Usage

### Referencing Queries in Experiments

Instead of embedding queries inline, reference them from the apps directory:

**Before (inline query):**
```yaml
# experiments/tpch-q1-memory-sf1.yaml
queries:
  - |
    SELECT l_returnflag, l_linestatus, ...
    FROM lineitem WHERE ...
```

**After (reference query file):**
```yaml
# experiments/tpch-q1-memory-sf1.yaml
query_file: "apps/tpch/queries/q01.sql"
connection:
  catalog: "memory"
  schema: "tpch_sf1"
```

### Benefits

1. **Reusability**: Run the same query on different systems/configurations
   ```
   experiments/
   ├── tpch-q1-memory-sf1.yaml      → apps/tpch/queries/q01.sql
   ├── tpch-q1-iceberg-sf1.yaml     → apps/tpch/queries/q01.sql
   └── tpch-q1-iceberg-sf10.yaml    → apps/tpch/queries/q01.sql
   ```

2. **Maintenance**: Fix a query once, all experiments benefit

3. **Verification**: Easy to compare against official TPC-H specification

4. **Documentation**: Each query file includes purpose and expected results

## Query Files

All query files follow this format:

```sql
-- TPC-H Query X: Query Name
--
-- Description of what the query does and why it's important
--
-- Expected result: Description of output

SELECT ...
FROM ...
WHERE ...;
```

## Getting Started

See `apps/tpch/README.md` for:
- Available queries and their characteristics
- Query selection rationale for dissertation research
- Performance considerations
- Testing instructions
