# Experiment Definitions

This directory contains experiment definition files in YAML format. Each experiment defines:
- SQL queries to execute
- Connection parameters
- Execution configuration (runs, timeouts, retries)
- Validation rules
- Metadata

## Quick Start Templates

Two template files are available to help you create new experiments:

- **TEMPLATE-minimal.yaml** - Minimal template with only essential fields (recommended for beginners)
- **TEMPLATE.yaml** - Complete template with all available options and detailed documentation

To create a new experiment:
```bash
# Copy the minimal template
cp experiments/templates/TEMPLATE-minimal.yaml experiments/my-experiment.yaml

# Or copy the complete template
cp experiments/templates/TEMPLATE.yaml experiments/my-experiment.yaml

# Edit your experiment file
# Then run it
tribench exp run experiments/my-experiment.yaml
```

## Experiment YAML Schema

```yaml
# Required fields
name: "experiment-name"              # Unique experiment identifier
description: "Description of experiment"
system: "trino"                      # Target system (currently only "trino")

# Optional: Connection parameters (override defaults)
connection:
  host: "localhost"
  port: 8080
  user: "tribench"
  catalog: "tpch"
  schema: "sf1"

# Optional: Execution parameters
runs: 3                              # Number of measurement runs (default: 1)
warmup_runs: 0                       # Warmup runs before measurement (default: 0)
timeout_seconds: 300                 # Query timeout in seconds (default: 300)
max_retries: 3                       # Max retry attempts (default: 3)

# Queries: Choose one or both
queries:                             # Inline SQL queries
  - "SELECT COUNT(*) FROM table1"
  - "SELECT * FROM table2 LIMIT 10"

query_files:                         # Or load from files
  - "queries/tpch/q1.sql"
  - "queries/tpch/q2.sql"

# Optional: Validation rules
validation:
  min_success_rate: 0.95                # Minimum % of successful runs
  max_execution_time_variance: 0.2      # Maximum variance (CoV)

# Optional: Metrics to collect
metrics:
  - execution_time
  - rows_returned
  - cpu_time
  - memory_usage
  - data_scanned

# Optional: Additional metadata
metadata:
  purpose: "Performance analysis"
  tags: ["benchmark", "tpch"]
```

## Example Experiments

### test-simple.yaml
Minimal smoke test with simple queries against Trino's built-in TPC-H tiny dataset.
Perfect for testing framework functionality.

**Usage:**
```bash
tribench exp run experiments/test-simple.yaml
```

### tpch-q1-sf1.yaml
TPC-H Query 1 (Pricing Summary Report) against Scale Factor 1 data.
Demonstrates full benchmarking workflow with multiple runs and validation.

**Usage:**
```bash
tribench exp run experiments/tpch-q1-sf1.yaml
tribench exp run experiments/tpch-q1-sf1.yaml --runs 10 --warmup 3
```

## Creating Custom Experiments

1. Copy an existing experiment YAML as a template
2. Modify the queries and parameters
3. Adjust validation rules for your use case
4. Run with `tribench exp run your-experiment.yaml`

## Query Files

For complex queries or query suites, create `.sql` files in `experiments/queries/` 
and reference them in your experiment YAML:

```yaml
query_files:
  - "queries/custom/analysis-query.sql"
```

## Results

Experiment results are stored in `results/` directory as JSON files:
- Individual run results: `{experiment-name}_{timestamp}.json`
- Aggregated statistics included in result files
- View with `tribench res show {filename}`

## Tips

- Start with `test-simple.yaml` to verify Trino is running
- Use `--dry-run` flag to validate configuration without execution
- Increase `runs` for better statistical significance (5-10 recommended)
- Use `warmup_runs` to prime caches for steady-state measurements
- Adjust `timeout_seconds` based on query complexity
- Set strict `max_execution_time_variance` for reproducibility testing

## Troubleshooting

**Connection Failed:**
- Ensure Trino is running: `tribench sys status trino`
- Start Trino if needed: `tribench sys start trino`
- Check connection parameters in experiment YAML

**Validation Failed:**
- Review validation rules (may be too strict)
- Check for environmental factors (load, resource contention)
- Increase `runs` for more stable measurements

**Query Timeout:**
- Increase `timeout_seconds` in experiment YAML
- Or override: `tribench exp run experiment.yaml --timeout 600`
