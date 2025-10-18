# Results Directory

This directory stores benchmark execution results and generated reports.

## Structure

```
results/
├── {suite_name}/                    # Results grouped by experiment suite
│   ├── {experiment_name}.run{N}/   # Individual experiment runs
│   │   ├── experiment.log          # Experiment execution log
│   │   ├── metrics.json           # Performance metrics
│   │   ├── system_logs/           # System-specific logs
│   │   │   ├── trino/
│   │   │   └── monitoring/
│   │   └── results.json           # Query results and timings
│   ├── suite_summary.json         # Suite-level aggregation
│   └── reports/                   # Generated reports
│       ├── performance.html
│       ├── plots/
│       └── raw_data.csv
└── archive/                       # Archived results
```

## Result Files

### experiment.log
Complete log of experiment execution including:
- Setup and teardown operations
- System status checks  
- Error messages and warnings
- Execution timeline

### metrics.json
Structured performance metrics:

```json
{
  "experiment": {
    "name": "tpch.sf1.query01",
    "suite": "tpch.sf1",
    "timestamp": "2024-01-01T12:00:00Z",
    "duration_ms": 15430
  },
  "queries": [
    {
      "name": "query01",
      "sql": "SELECT l_returnflag...",
      "execution_time_ms": 12450,
      "rows_returned": 4,
      "data_scanned_mb": 759.2,
      "cpu_time_ms": 45600,
      "memory_peak_mb": 2048
    }
  ],
  "system": {
    "trino_version": "434",
    "cluster_nodes": 1,
    "total_memory_mb": 8192,
    "total_cpu_cores": 4
  }
}
```

### results.json
Query results for validation:

```json
{
  "query01": {
    "columns": ["l_returnflag", "l_linestatus", "sum_qty"],
    "rows": [
      ["A", "F", 37734107.00],
      ["N", "F", 991417.00],
      ["N", "O", 74476040.00],
      ["R", "F", 37719753.00]
    ],
    "row_count": 4,
    "checksum": "md5:abc123..."
  }
}
```

## Archiving Results

Results can be archived for long-term storage:

```bash
# Archive specific suite
tribench.sh res archive tpch.sf1

# Archive all results older than 30 days
tribench.sh res archive --older-than 30d
```

## Result Analysis

Generate reports and visualizations:

```bash
# HTML performance report
tribench.sh res analyze tpch.sf1 --format html

# CSV data export
tribench.sh res export tpch.sf1 --format csv

# Compare multiple suites
tribench.sh res compare tpch.sf1 tpch.sf10
```
