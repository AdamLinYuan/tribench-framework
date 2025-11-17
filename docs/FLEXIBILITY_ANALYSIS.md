# TriBench Flexibility Analysis - PEEL Comparison

**Date**: 18 October 2025  
**Purpose**: Identify hardcoded patterns in TriBench and recommend PEEL-inspired improvements

---

## Executive Summary

After studying the PEEL framework architecture and analyzing your TriBench codebase, I've identified **5 major areas** where your implementation could be more flexible and extensible. While your recent dataset schema refactoring was excellent, there are deeper architectural patterns from PEEL that would significantly improve TriBench's flexibility.

---


## 3. ⚠️ MEDIUM: Missing System Lifespan Management

### Current Problem

**No concept of system lifecycle scopes** in your System abstraction.

PEEL has sophisticated lifespan management:
- **PROVIDED**: System already running (e.g., production database)
- **SUITE**: Start once for entire experiment suite, teardown at end
- **EXPERIMENT**: Start/stop per experiment
- **RUN**: Start/stop per individual run

Your current approach: Systems are manually started/stopped via CLI with no automatic lifecycle management.

### PEEL's Approach

```scala
// From Lifespan.scala
case object Lifespan extends Enumeration {
  type Lifespan = Value
  final val RUN, EXPERIMENT, SUITE, PROVIDED = Value
}

// Systems declare their lifespan
@Bean(name = Array("hdfs-2.7.1"))
def `hdfs-2.7.1`: HDFS2 = new HDFS2(
  version  = "2.7.1",
  lifespan = Lifespan.SUITE,  // Start once per suite
  ...
)

@Bean(name = Array("flink-0.9.0"))
def `flink-0.9.0`: Flink = new Flink(
  version  = "0.9.0",
  lifespan = Lifespan.EXPERIMENT,  // Restart per experiment
  ...
)
```

**Automatic Lifecycle** (from `suite/Run.scala`):
```scala
// Setup Suite
for (s <- systems if s.lifespan == Lifespan.SUITE) s.setUp()

// For each experiment
for (e <- experiments) {
  // Setup experiment-level systems
  for (s <- systems if s.lifespan == Lifespan.EXPERIMENT) s.setUp()
  
  // For each run
  for (r <- runs) {
    for (s <- systems if s.lifespan == Lifespan.RUN) s.setUp()
    r.execute()
    for (s <- systems if s.lifespan == Lifespan.RUN) s.tearDown()
  }
  
  // Teardown experiment-level
  for (s <- systems if s.lifespan == Lifespan.EXPERIMENT) s.tearDown()
}

// Teardown suite
for (s <- systems if s.lifespan == Lifespan.SUITE) s.tearDown()
```

### Recommended Solution

**Add Lifespan to System abstraction**:

```python
# lib/tribench/core/system.py
from enum import Enum

class Lifespan(Enum):
    """System lifecycle scope."""
    PROVIDED = 0   # Already running, don't manage
    SUITE = 1      # Start once per suite
    EXPERIMENT = 2 # Restart per experiment
    RUN = 3        # Restart per run
    
    def __lt__(self, other):
        return self.value < other.value


class System(ABC):
    """Base class for all systems."""
    
    def __init__(self, name: str, config, lifespan: Lifespan = Lifespan.EXPERIMENT):
        self.name = name
        self.config = config
        self.lifespan = lifespan
    
    # ... rest of System class


# lib/tribench/core/experiment_suite.py
class ExperimentSuite:
    """
    Collection of related experiments with automatic system lifecycle.
    Inspired by PEEL's ExperimentSuite.
    """
    
    def __init__(self, 
                 name: str,
                 experiments: List[Experiment],
                 systems: List[System]):
        self.name = name
        self.experiments = experiments
        self.systems = systems
    
    def run(self):
        """Execute all experiments with proper system lifecycle."""
        
        # Setup suite-level systems
        logger.info("Setting up SUITE lifespan systems")
        for sys in self._systems_with_lifespan(Lifespan.SUITE):
            sys.setup()
            sys.start()
        
        try:
            for exp in self.experiments:
                self._run_experiment(exp)
        finally:
            # Teardown suite-level systems
            logger.info("Tearing down SUITE lifespan systems")
            for sys in self._systems_with_lifespan(Lifespan.SUITE):
                sys.stop()
                sys.teardown()
    
    def _run_experiment(self, exp: Experiment):
        """Run single experiment with lifecycle management."""
        
        # Setup experiment-level systems
        for sys in self._systems_with_lifespan(Lifespan.EXPERIMENT):
            sys.setup()
            sys.start()
        
        try:
            for run_id in range(exp.config.runs):
                self._run_single(exp, run_id)
        finally:
            # Teardown experiment-level
            for sys in self._systems_with_lifespan(Lifespan.EXPERIMENT):
                sys.stop()
                sys.teardown()
    
    def _run_single(self, exp: Experiment, run_id: int):
        """Run single execution with RUN lifecycle."""
        
        # Setup run-level systems
        for sys in self._systems_with_lifespan(Lifespan.RUN):
            sys.setup()
            sys.start()
        
        try:
            exp.run()
        finally:
            for sys in self._systems_with_lifespan(Lifespan.RUN):
                sys.stop()
                sys.teardown()
    
    def _systems_with_lifespan(self, lifespan: Lifespan) -> List[System]:
        """Filter systems by lifespan."""
        return [s for s in self.systems if s.lifespan == lifespan]
```

**Benefits**:
- ✅ Automatic system lifecycle management
- ✅ No manual start/stop commands needed
- ✅ Prevents resource leaks
- ✅ Matches PEEL's sophisticated lifecycle model

---

## 4. ⚠️ MEDIUM: Missing ExperimentSequence Pattern

### Current Problem

**No parameterized experiment generation**. You must manually create separate YAML files for:
- TPC-H Q1 at SF1, SF10, SF100
- TPC-H Q1 on Trino 434, Trino 435
- TPC-H Q1 with 1 worker, 4 workers, 8 workers

This leads to **YAML explosion** and **copy-paste errors**.

### PEEL's Approach

**ExperimentSequence with Parameter Substitution**:

```scala
// From experiments.scala
new ExperimentSuite(
  new ExperimentSequence(
    parameters = new SimpleParameters(
      paramName = "topXXX",  // Parameter to vary
      paramVals = Seq("top005", "top010", "top020")  // Values
    ),
    prototypes = Seq(
      // Prototype uses __topXXX__ placeholder
      new FlinkExperiment(
        name = "wordcount.flink.__topXXX__",  // Becomes wordcount.flink.top005, etc.
        config = ConfigFactory.parseString(
          """
          |system.default.config.slaves = ${env.slaves.__topXXX__.hosts}
          |system.default.config.parallelism = ${env.slaves.__topXXX__.parallelism}
          """.stripMargin
        ),
        ...
      )
    )
  )
)
```

**Result**: 1 prototype × 3 parameter values = **3 experiments generated automatically**.

### Recommended Solution

**Create ExperimentSequence Builder**:

```python
# lib/tribench/core/experiment_sequence.py
from typing import List, Dict, Any
from itertools import product

class ExperimentSequence:
    """
    Generate multiple experiments by varying parameters.
    Inspired by PEEL's ExperimentSequence.
    """
    
    def __init__(self, 
                 base_config: ExperimentConfig,
                 parameters: Dict[str, List[Any]]):
        """
        Args:
            base_config: Template experiment config with placeholders
            parameters: Dict of parameter_name -> [values]
        
        Example:
            parameters = {
                'scale_factor': [1, 10, 100],
                'workers': [1, 4, 8]
            }
        """
        self.base_config = base_config
        self.parameters = parameters
    
    def generate(self) -> List[ExperimentConfig]:
        """Generate all parameter combinations."""
        
        experiments = []
        
        # Cartesian product of all parameter values
        param_names = list(self.parameters.keys())
        param_values = list(self.parameters.values())
        
        for combination in product(*param_values):
            # Create mapping for this combination
            param_map = dict(zip(param_names, combination))
            
            # Create new config with substituted values
            exp_config = self._substitute_parameters(
                self.base_config, 
                param_map
            )
            experiments.append(exp_config)
        
        return experiments
    
    def _substitute_parameters(self, 
                               config: ExperimentConfig,
                               params: Dict[str, Any]) -> ExperimentConfig:
        """Replace __PARAM__ placeholders with actual values."""
        
        import copy
        import re
        
        new_config = copy.deepcopy(config)
        
        # Substitute in name
        for param_name, param_value in params.items():
            placeholder = f"__{param_name}__"
            new_config.name = new_config.name.replace(
                placeholder, 
                str(param_value)
            )
        
        # Substitute in metadata
        new_config.metadata.update(params)
        
        # Substitute in queries (if using parameterized SQL)
        new_queries = []
        for query in new_config.queries:
            for param_name, param_value in params.items():
                placeholder = f"__{param_name}__"
                query = query.replace(placeholder, str(param_value))
            new_queries.append(query)
        new_config.queries = new_queries
        
        return new_config


# lib/tribench/core/experiment_suite.py
class ExperimentSuite:
    """Suite can now contain sequences."""
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ExperimentSuite":
        """
        Load suite from YAML with parameter expansion.
        
        Example YAML:
        ```yaml
        name: tpch-scale-analysis
        experiments:
          - template: experiments/tpch-q1-template.yaml
            parameters:
              scale_factor: [1, 10, 100]
              runs: [3, 5]
        ```
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        
        experiments = []
        
        for exp_spec in data['experiments']:
            if 'parameters' in exp_spec:
                # Generate sequence
                base_config = ExperimentConfig.from_yaml(
                    exp_spec['template']
                )
                sequence = ExperimentSequence(
                    base_config,
                    exp_spec['parameters']
                )
                experiments.extend(sequence.generate())
            else:
                # Single experiment
                experiments.append(
                    ExperimentConfig.from_yaml(exp_spec['path'])
                )
        
        return cls(name=data['name'], experiments=experiments)
```

**Usage Example**:

```yaml
# experiments/tpch-q1-template.yaml
name: tpch.q1.sf__scale_factor__
description: TPC-H Q1 at scale factor __scale_factor__
system: trino
dataset: tpch-sf__scale_factor__
query_files:
  - queries/tpch/q1.sql
runs: __runs__

# experiments/suites/tpch-scalability.yaml
name: tpch-scalability-study
experiments:
  - template: experiments/tpch-q1-template.yaml
    parameters:
      scale_factor: [1, 10, 100, 1000]
      runs: [3, 5, 10]
```

**Result**: 1 template × 4 scales × 3 run configs = **12 experiments generated** from 2 YAML files!

**Benefits**:
- ✅ No YAML duplication
- ✅ Systematic parameter exploration
- ✅ Follows PEEL's ExperimentSequence pattern
- ✅ Critical for dissertation: Vary Iceberg features systematically

---

## 5. ⚠️ LOW: Missing Configuration Override Hierarchy

### Current Problem

**No clean way to override config at different levels**:
- Suite-level overrides (e.g., "all experiments use Trino 434")
- Experiment-level overrides (e.g., "this experiment needs 16GB heap")
- Run-level overrides (e.g., CLI flag `--timeout 600`)

Currently mixing CLI flags and YAML with no clear precedence.

### PEEL's Approach

**Hierarchical Configuration Merging**:

```scala
// From loadConfig in experiment/Run.scala
e.config = loadConfig(graph, e)

// loadConfig merges in order:
// 1. reference.conf (defaults)
// 2. Host config
// 3. Suite config  
// 4. Experiment config
// 5. CLI overrides

// Later configs override earlier ones
```

**You already have this partially** in `ConfigurationLoader`, but it's not integrated with experiments!

### Recommended Solution

**Extend ExperimentConfig.from_yaml to merge hierarchy**:

```python
# lib/tribench/core/experiment.py
@dataclass
class ExperimentConfig:
    
    @classmethod
    def from_yaml(cls, 
                  yaml_path: Path,
                  suite_config: Optional[Dict] = None,
                  cli_overrides: Optional[Dict] = None) -> "ExperimentConfig":
        """
        Load with hierarchical merging.
        
        Precedence (highest to lowest):
        1. CLI overrides
        2. Experiment YAML
        3. Suite-level defaults
        4. Global defaults
        """
        
        # Load experiment YAML
        with open(yaml_path) as f:
            exp_data = yaml.safe_load(f)
        
        # Merge suite defaults (if provided)
        if suite_config:
            exp_data = {**suite_config, **exp_data}
        
        # Apply CLI overrides (if provided)
        if cli_overrides:
            exp_data = {**exp_data, **cli_overrides}
        
        # Create config
        return cls(**exp_data)


# lib/tribench/core/experiment_suite.py
class ExperimentSuite:
    
    def __init__(self, 
                 name: str,
                 default_config: Optional[Dict] = None):
        """
        Args:
            default_config: Suite-level defaults applied to all experiments
        """
        self.name = name
        self.default_config = default_config or {}
    
    @classmethod
    def from_yaml(cls, yaml_path: Path):
        """
        Load suite with defaults.
        
        Example:
        ```yaml
        name: tpch-suite
        defaults:
          system: trino
          runs: 3
          timeout_seconds: 300
        experiments:
          - path: experiments/q1.yaml
          - path: experiments/q6.yaml
            runs: 5  # Override suite default
        ```
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        
        suite = cls(
            name=data['name'],
            default_config=data.get('defaults', {})
        )
        
        # Load experiments with suite defaults
        for exp_spec in data['experiments']:
            config = ExperimentConfig.from_yaml(
                exp_spec['path'],
                suite_config=suite.default_config
            )
            suite.add_experiment(config)
        
        return suite
```

**Benefits**:
- ✅ DRY: Set common config once at suite level
- ✅ Clear override precedence
- ✅ Matches PEEL's hierarchical config

---

## Implementation Priority

### Phase 1: Critical (Week of Oct 21)
1. **System Registry** - Foundation for extensibility
2. **Experiment Registry** - Enables multi-system support
3. **ExperimentSuite with Lifespan** - Proper lifecycle

### Phase 2: Important (Week of Oct 28)
4. **ExperimentSequence** - Parameter exploration
5. **Config Hierarchy** - Clean overrides

---

## Benefits for Dissertation

1. **Extensibility**: Easy to add PostgreSQL, Spark comparisons
2. **Iceberg Feature Exploration**: ExperimentSequence perfect for varying:
   - Table formats (Parquet, ORC, Avro)
   - Partition strategies
   - Compaction policies
   - Time travel depths
3. **Reproducibility**: Lifespan management prevents "forgot to restart Trino" issues
4. **Professional Software Engineering**: Demonstrates design patterns, not just scripts

---

## Migration Path

All changes are **backward compatible** via deprecation:

```python
# Old way still works
experiment = TrinoExperiment(config)

# But warns
logger.warning("Direct instantiation deprecated. Use ExperimentRegistry.create()")

# New way
experiment = ExperimentRegistry.create(config)
```

No need to rewrite existing experiments immediately!

---

## Conclusion

Your dataset schema refactoring was a great first step toward PEEL-style flexibility. These 5 patterns would complete the transformation:

4. ⚠️ **System lifespans** - MISSING (no automatic lifecycle)
5. ⚠️ **Experiment sequences** - MISSING (YAML explosion)
6. ⚠️ **Config hierarchy** - PARTIAL (ConfigLoader exists but not integrated)

Implementing these would make TriBench a **true PEEL successor** in Python, not just PEEL-inspired.
