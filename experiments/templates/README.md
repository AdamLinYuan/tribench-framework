# Experiment Suite Templates

This directory contains YAML templates for creating experiment suites in TriBench.

## Available Templates

### 1. `suite-template-simple.yaml`
**Purpose**: Basic suite with minimal configuration  
**Use When**: You want all experiments to share the same configuration  
**Features**:
- Single set of defaults
- All experiments inherit same settings
- No per-experiment overrides

**Example Use Case**: Running the same set of queries with consistent configuration

---

### 2. `suite-template-advanced.yaml`
**Purpose**: Full-featured suite with per-experiment customization  
**Use When**: Different experiments need different configurations  
**Features**:
- Comprehensive suite defaults
- Per-experiment overrides
- Monitoring configuration
- Metadata tracking
- Different validation rules per experiment

**Example Use Case**: Complex benchmarking with varied requirements

---

### 3. `suite-template-tpch.yaml`
**Purpose**: TPC-H benchmark suite  
**Use When**: Running standard TPC-H queries  
**Features**:
- Organized by query complexity
- Different timeouts for complex queries
- Scale factor configuration
- All 22 TPC-H queries (commented examples)

**Example Use Case**: Standard TPC-H benchmark execution

---

### 4. `suite-template-iceberg.yaml`
**Purpose**: Apache Iceberg table format testing  
**Use When**: Testing Iceberg-specific features  
**Features**:
- Iceberg catalog configuration
- Time travel queries
- Schema evolution tests
- Partition pruning tests
- Format comparison capabilities

**Example Use Case**: Iceberg feature validation and performance testing

---

### 5. `suite-template-multi-system.yaml`
**Purpose**: Cross-system performance comparison  
**Use When**: Comparing same queries across different engines  
**Features**:
- Multiple system configurations
- Same query on different systems
- Per-system metadata tracking
- Version tracking

**Example Use Case**: Trino vs Spark performance comparison

---

### 6. `suite-template-scalability.yaml`
**Purpose**: Data scalability testing  
**Use When**: Testing how performance scales with data size  
**Features**:
- Multiple scale factors (SF1, SF10, SF100)
- Adjusted timeouts per scale
- Adjusted run counts per scale
- Resource monitoring

**Example Use Case**: Understanding query performance at different data scales

---

### 7. `suite-template-regression.yaml`
**Purpose**: Performance regression detection  
**Use When**: Validating no performance degradation  
**Features**:
- High run counts for statistics
- Stricter validation
- Baseline time tracking
- Regression thresholds
- Priority levels

**Example Use Case**: CI/CD performance validation

---

## How to Use Templates

### 1. Copy Template
```bash
cp experiments/templates/suite-template-simple.yaml experiments/suites/my-suite.yaml
```

### 2. Customize Configuration
Edit the copied file:
- Change `name` and `description`
- Adjust `defaults` section
- Update `experiments` list with your experiment paths
- Add or remove per-experiment overrides

### 3. Run Suite
```bash
tribench suite run experiments/suites/my-suite.yaml
```

## Configuration Hierarchy

Configurations merge in this order (later overrides earlier):

1. **Suite defaults** (`defaults:` section)
2. **Experiment YAML** (the referenced experiment file)
3. **Per-experiment overrides** (in suite under each experiment)
4. **CLI flags** (`--runs`, `--timeout`, etc.)

### Example:
```yaml
defaults:
  runs: 3  # Suite default

experiments:
  - path: ../my-exp.yaml  # my-exp.yaml has runs: 5
    runs: 10  # Per-experiment override
```

**Result**: Experiment runs 10 times (CLI can override to any value)

## Common Patterns

### Pattern 1: Quick Smoke Test
```yaml
defaults:
  runs: 1
  warmup_runs: 0
  timeout_seconds: 60
```

### Pattern 2: Production Benchmark
```yaml
defaults:
  runs: 10
  warmup_runs: 3
  timeout_seconds: 1800
  monitoring:
    enabled: true
```

### Pattern 3: Development Testing
```yaml
defaults:
  runs: 2
  warmup_runs: 1
  validation:
    min_success_rate: 0.90  # Relaxed
```

### Pattern 4: Stress Testing
```yaml
defaults:
  runs: 100
  timeout_seconds: 3600
  max_retries: 5
```

## Best Practices

1. **Name Descriptively**: Use clear suite names that indicate purpose
2. **Set Appropriate Defaults**: Choose sensible defaults for most experiments
3. **Override When Needed**: Only override when an experiment needs different settings
4. **Document Intent**: Add descriptions to experiments explaining why they exist
5. **Use Metadata**: Tag experiments with relevant metadata for analysis
6. **Version Control**: Keep suite YAMLs in git to track changes over time
7. **Start Simple**: Begin with simple template, add complexity as needed

## Validation Configuration

All templates support validation configuration:

```yaml
validation:
  min_success_rate: 0.95  # 95% of queries must succeed
  max_execution_time_variance: 0.2  # 20% coefficient of variation
```

- **min_success_rate**: Fraction of queries that must complete successfully (0.0 to 1.0)
- **max_execution_time_variance**: Maximum acceptable coefficient of variation in execution times

## Monitoring Configuration

Enable resource monitoring:

```yaml
monitoring:
  enabled: true
  interval_seconds: 5
  metrics:
    - cpu_usage
    - memory_usage
    - disk_io
    - network_io
```

## Tips

- **Start with simple template** and add complexity as needed
- **Test with --dry-run** before full execution
- **Use --verbose** to see detailed configuration merging
- **Check suite structure** with `tribench suite show`
- **Filter experiments** during development with `--exp <pattern>`
- **Override runs** for quick tests with `--runs 1`

## Examples

### Example 1: Quick Development Test
```bash
tribench suite run experiments/suites/my-suite.yaml --runs 1 --dry-run
```

### Example 2: Run Specific Experiments
```bash
tribench suite run experiments/suites/tpch-suite.yaml --exp q01
```

### Example 3: Production Benchmark
```bash
tribench suite run experiments/suites/regression-suite.yaml --verbose
```

### Example 4: Override Timeout
```bash
tribench suite run experiments/suites/scalability-suite.yaml --timeout 3600
```

## Getting Help

- View available suites: `tribench suite list`
- Show suite details: `tribench suite show experiments/suites/my-suite.yaml`
- Check suite syntax: `tribench suite show experiments/suites/my-suite.yaml --dry-run`
- See all options: `tribench suite run --help`

## Related Documentation

- [Suite Execution Flow](../../docs/SUITE_EXECUTION_FLOW.md)
- [Smart Lifecycle Behavior](../../docs/SMART_LIFECYCLE_BEHAVIOR.md)
- [Experiment Templates](../experiments/templates/)
- [Configuration Guide](../../config/README.md)
