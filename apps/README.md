# Apps Directory

This directory contains benchmark applications and SQL workloads.

## Structure

```
apps/
├── tpch/                   # TPC-H benchmark queries
│   ├── queries/           # Individual SQL query files
│   └── workloads/         # Predefined workload sets
├── tpcds/                 # TPC-DS benchmark queries  
├── microbench/            # Microbenchmark queries
└── custom/                # Custom user workloads
```

## File Formats

- **SQL files**: Individual queries (`.sql`)
- **Workload definitions**: JSON/YAML configurations defining query sequences
- **Parameters**: Parameterized queries with variable substitution

## Examples

### Single Query
```sql
-- apps/tpch/queries/query01.sql
SELECT 
    l_returnflag,
    l_linestatus,
    sum(l_quantity) as sum_qty
FROM lineitem 
WHERE l_shipdate <= date '1998-09-02'
GROUP BY l_returnflag, l_linestatus
ORDER BY l_returnflag, l_linestatus;
```

### Workload Definition
```yaml
# apps/tpch/workloads/sf1_standard.yaml
name: "TPC-H SF1 Standard Workload"
description: "Standard TPC-H queries on scale factor 1"
queries:
  - query01.sql
  - query02.sql
  - query03.sql
parameters:
  scale_factor: 1
  date_offset: 90
concurrency: 1
iterations: 3
```
