# Result & Analysis Engine Improvement Plan

**Created**: January 9, 2026  
**Purpose**: Enhance TriBench result/analysis engine to support dissertation research goals  
**Status**: 📋 Planning

---

## Dissertation Research Goals

Based on your research objectives, you need to compare:

| Comparison Type | Current Support | Gap |
|-----------------|-----------------|-----|
| **Same experiments, repeated executions** | ✅ Partial | Need variance analysis, reproducibility metrics |
| **Local vs GCP (infrastructure comparison)** | ❌ None | Need environment metadata, cross-environment comparison |
| **Framework overhead measurement** | ❌ None | Need raw Trino timing vs framework timing |
| **Different configurations** | ❌ None | Need config tracking and comparison |
| **Different benchmarks/query sets** | ✅ Partial | Need benchmark categorization, workload profiles |

---

## Phase 1: Enhanced Metrics Capture (Priority: HIGH)

### 1.1 Add Missing Trino Metrics to Database Schema

**New columns in `QueryExecution` model:**

```python
# Add to lib/tribench/storage/models.py

# Spill metrics (memory pressure)
spilled_bytes = Column(BigInteger, nullable=True)

# Parallelism metrics
total_splits = Column(Integer, nullable=True)
completed_splits = Column(Integer, nullable=True)

# Task metrics
total_tasks = Column(Integer, nullable=True)
completed_tasks = Column(Integer, nullable=True)
failed_tasks = Column(Integer, nullable=True)

# Cumulative memory (total memory*time)
cumulative_memory_bytes = Column(BigInteger, nullable=True)

# Timing breakdown (currently only stored in metadata JSON)
planning_time_ms = Column(Integer, nullable=True)  # Already exists but NOT populated
analysis_time_ms = Column(Integer, nullable=True)  # Already exists but NOT populated

# Stage information
total_stages = Column(Integer, nullable=True)

# Framework overhead measurement
framework_overhead_ms = Column(Integer, nullable=True)  # NEW: Time spent outside Trino
```

**Files to modify:**
- `lib/tribench/storage/models.py`
- `lib/tribench/storage/result/query_store.py`
- `lib/tribench/experiments/trino/storage.py`
- `lib/tribench/experiments/query_executor.py`

**Estimated effort:** 2-3 hours

---

### 1.2 Add Environment/Infrastructure Metadata

**New `Environment` model:**

```python
# lib/tribench/storage/models.py

class Environment(Base):
    """Captures execution environment for reproducibility and comparison."""
    __tablename__ = "environments"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True)  # "local-docker", "gcp-gke-4node"
    
    # Infrastructure type
    infra_type = Column(String(50))  # "local", "gcp", "aws", "kubernetes"
    deployment_mode = Column(String(50))  # "docker-compose", "kubernetes", "bare-metal"
    
    # Compute resources
    total_cpu_cores = Column(Integer)
    total_memory_gb = Column(Float)
    node_count = Column(Integer, default=1)
    
    # Trino cluster configuration
    trino_version = Column(String(50))
    coordinator_memory_gb = Column(Float)
    worker_memory_gb = Column(Float)
    worker_count = Column(Integer)
    
    # Network/storage
    storage_type = Column(String(50))  # "local-ssd", "gcs", "s3", "minio"
    network_type = Column(String(50))  # "local", "vpc", "cross-region"
    
    # Platform details (auto-detected)
    os_name = Column(String(100))
    os_version = Column(String(50))
    python_version = Column(String(20))
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    metadata = Column(JSON)  # Additional platform-specific info
```

**Add environment_id to Experiment:**

```python
# In Experiment model
environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True, index=True)
environment = relationship("Environment", back_populates="experiments")
```

**Files to modify:**
- `lib/tribench/storage/models.py`
- `lib/tribench/storage/result/experiment_store.py`
- `lib/tribench/experiments/trino/experiment.py`
- New: `lib/tribench/utils/environment.py` (auto-detection)

**Estimated effort:** 3-4 hours

---

### 1.3 Add Framework Overhead Tracking

**Goal:** Measure how much time the framework spends vs actual Trino query execution.

**Implementation:**

```python
# In query_executor.py

def execute_query(self, query: str, ...) -> Tuple[List[Tuple], Dict[str, Any]]:
    framework_start = time.perf_counter_ns()  # High-precision timer
    
    # ... connection setup, preparation ...
    
    trino_start = time.perf_counter_ns()
    self._cursor.execute(query)
    rows = self._cursor.fetchall()
    trino_end = time.perf_counter_ns()
    
    # ... result processing, stats collection ...
    
    framework_end = time.perf_counter_ns()
    
    metadata["trino_time_ns"] = trino_end - trino_start
    metadata["total_time_ns"] = framework_end - framework_start
    metadata["framework_overhead_ns"] = (framework_end - framework_start) - (trino_end - trino_start)
    metadata["framework_overhead_percent"] = metadata["framework_overhead_ns"] / metadata["total_time_ns"] * 100
```

**Files to modify:**
- `lib/tribench/experiments/query_executor.py`
- `lib/tribench/storage/models.py`
- `lib/tribench/storage/result/query_store.py`

**Estimated effort:** 1-2 hours

---

## Phase 2: Enhanced Analysis Capabilities (Priority: HIGH)

### 2.1 New Analyzer: Infrastructure Comparison

**New file: `lib/tribench/analysis/infrastructure.py`**

```python
class InfrastructureAnalyzer:
    """Compare performance across different execution environments."""
    
    def compare_environments(
        self,
        environment_ids: List[int],
        experiment_name: Optional[str] = None,
        normalize_by: str = "cpu_cores"  # or "memory_gb", "cost"
    ) -> Dict[str, Any]:
        """
        Compare same experiments run on different infrastructures.
        
        Returns:
            - Per-environment performance summaries
            - Normalized comparison (e.g., queries/second per CPU core)
            - Cost-efficiency analysis (if cost data available)
            - Recommendations
        """
        
    def calculate_efficiency_ratio(
        self,
        local_experiment_id: int,
        cloud_experiment_id: int,
        cost_per_hour: float = None
    ) -> Dict[str, Any]:
        """
        Compare local vs cloud efficiency.
        
        Returns:
            - Speed ratio (cloud_time / local_time)
            - Cost per query
            - Break-even analysis
        """
```

**Estimated effort:** 4-5 hours

---

### 2.2 New Analyzer: Reproducibility Analysis

**New file: `lib/tribench/analysis/reproducibility.py`**

```python
class ReproducibilityAnalyzer:
    """Analyze variance and reproducibility across repeated executions."""
    
    def analyze_variance(
        self,
        experiment_id: int,
        min_runs: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze variance across multiple runs of the same experiment.
        
        Returns:
            - Coefficient of variation (CV) per query
            - Stability score (% of queries with CV < threshold)
            - Warmup effect analysis
            - Run-to-run delta
        """
        
    def analyze_warmup_effect(
        self,
        experiment_id: int
    ) -> Dict[str, Any]:
        """
        Analyze performance improvement from warmup runs.
        
        Returns:
            - First run vs subsequent runs comparison
            - Warmup stabilization point
            - Recommended warmup runs
        """
        
    def calculate_required_runs(
        self,
        experiment_id: int,
        target_margin_of_error: float = 0.05,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculate number of runs needed for statistical significance.
        
        Uses observed variance to recommend run count for target precision.
        """
```

**Estimated effort:** 3-4 hours

---

### 2.3 New Analyzer: Configuration Comparison

**New file: `lib/tribench/analysis/configuration.py`**

```python
class ConfigurationAnalyzer:
    """Compare experiments with different configurations."""
    
    def compare_configs(
        self,
        experiment_ids: List[int],
        config_keys: List[str] = None  # Specific config keys to highlight
    ) -> Dict[str, Any]:
        """
        Compare experiments with different configurations.
        
        Returns:
            - Config diff between experiments
            - Performance impact per config change
            - Best performing configuration
        """
        
    def analyze_config_sensitivity(
        self,
        experiment_ids: List[int],
        variable_config_key: str  # e.g., "trino.memory.heap_size"
    ) -> Dict[str, Any]:
        """
        Analyze how a specific config parameter affects performance.
        
        Returns:
            - Parameter value vs performance correlation
            - Optimal value recommendation
            - Diminishing returns analysis
        """
```

**Estimated effort:** 3-4 hours

---

### 2.4 Enhanced Comparison Analyzer

**Update: `lib/tribench/analysis/comparison.py`**

Add methods for multi-dimensional comparison:

```python
# Add to ComparisonAnalyzer class

def compare_multi_dimensional(
    self,
    experiment_ids: List[int],
    dimensions: List[str] = None  # ["environment", "config", "dataset"]
) -> Dict[str, Any]:
    """
    Multi-dimensional comparison across experiments.
    
    Groups experiments by specified dimensions and compares performance.
    """
    
def generate_comparison_matrix(
    self,
    experiment_ids: List[int],
    metric: str = "mean_execution_time"
) -> Dict[str, Any]:
    """
    Generate N x M comparison matrix for all query pairs.
    
    Useful for identifying which queries behave differently across experiments.
    """
```

**Estimated effort:** 2-3 hours

---

## Phase 3: Benchmark Categorization (Priority: MEDIUM)

### 3.1 Query Workload Classification

**New file: `lib/tribench/analysis/workload.py`**

```python
class WorkloadAnalyzer:
    """Analyze and categorize benchmark workloads."""
    
    def classify_queries(
        self,
        experiment_id: int
    ) -> Dict[str, Any]:
        """
        Classify queries by characteristics.
        
        Categories:
            - scan_heavy: High input_bytes, low join count
            - join_heavy: Multiple table joins
            - aggregation_heavy: GROUP BY, SUM, COUNT dominant
            - analytical: Complex with window functions
            - simple: Point lookups, small result sets
        """
        
    def create_workload_profile(
        self,
        experiment_id: int
    ) -> Dict[str, Any]:
        """
        Create a workload profile for an experiment.
        
        Returns:
            - Query complexity distribution
            - Resource usage patterns
            - Bottleneck identification (CPU, memory, I/O, network)
        """
        
    def compare_workload_profiles(
        self,
        experiment_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Compare workload profiles across different benchmarks.
        
        Useful for: "How does TPC-H compare to my custom workload?"
        """
```

**Estimated effort:** 4-5 hours

---

### 3.2 Add Benchmark Metadata to Experiments

**Update Experiment model:**

```python
# In Experiment model
benchmark_type = Column(String(50), nullable=True, index=True)  # "tpch", "tpcds", "custom"
benchmark_scale_factor = Column(Float, nullable=True)
query_categories = Column(JSON, nullable=True)  # {"scan": ["q1", "q6"], "join": ["q3", "q5"]}
```

**Estimated effort:** 1-2 hours

---

## Phase 4: CLI Enhancements (Priority: MEDIUM)

### 4.1 New Analysis Commands

```bash
# Infrastructure comparison
tribench res analyze infra <exp_id_1> <exp_id_2> [--normalize-by cpu|memory|cost]

# Reproducibility analysis
tribench res analyze reproducibility <exp_id> [--min-runs 5]
tribench res analyze warmup <exp_id>

# Configuration comparison
tribench res analyze config <exp_id_1> <exp_id_2> [--show-diff]
tribench res analyze sensitivity <exp_ids...> --param "trino.memory"

# Workload analysis
tribench res analyze workload <exp_id> [--classify]
tribench res analyze workload-compare <exp_ids...>

# Framework overhead
tribench res analyze overhead <exp_id>

# Generate dissertation-ready reports
tribench res report reproducibility <exp_id> --format latex
tribench res report comparison <exp_ids...> --output report.pdf
```

**Estimated effort:** 4-6 hours

---

### 4.2 Report Generation for Dissertation

**New file: `lib/tribench/analysis/report.py`**

```python
class ReportGenerator:
    """Generate dissertation-ready reports and visualizations."""
    
    def generate_reproducibility_report(
        self,
        experiment_id: int,
        output_format: str = "latex"  # "latex", "markdown", "html"
    ) -> str:
        """
        Generate reproducibility analysis report.
        
        Includes:
            - Table: Per-query variance statistics
            - Figure: Execution time box plots
            - Figure: Run-to-run correlation
            - LaTeX-formatted tables
        """
        
    def generate_comparison_report(
        self,
        experiment_ids: List[int],
        comparison_type: str = "infrastructure",  # "infrastructure", "config", "benchmark"
        output_format: str = "latex"
    ) -> str:
        """
        Generate comparison report.
        
        Includes:
            - Table: Performance comparison matrix
            - Figure: Bar charts with error bars
            - Statistical significance indicators
        """
        
    def generate_overhead_report(
        self,
        experiment_id: int
    ) -> str:
        """
        Generate framework overhead analysis report.
        
        Includes:
            - Pie chart: Time breakdown (Trino vs framework)
            - Table: Per-query overhead statistics
            - Recommendations for reducing overhead
        """
```

**Estimated effort:** 5-6 hours

---

## Phase 5: Visualization Support (Priority: LOW)

### 5.1 Plotting Utilities

**New file: `lib/tribench/analysis/visualization.py`**

```python
class Visualizer:
    """Generate plots for analysis results."""
    
    def plot_execution_times_boxplot(self, experiment_id: int, output: Path) -> Path
    def plot_comparison_bars(self, experiment_ids: List[int], output: Path) -> Path
    def plot_scalability_curve(self, experiment_ids: List[int], workers: List[int], output: Path) -> Path
    def plot_warmup_effect(self, experiment_id: int, output: Path) -> Path
    def plot_overhead_breakdown(self, experiment_id: int, output: Path) -> Path
    def plot_infrastructure_comparison(self, experiment_ids: List[int], output: Path) -> Path
```

**Dependencies:** `matplotlib`, `seaborn` (optional)

**Estimated effort:** 4-5 hours

---

## Implementation Priorities

| Priority | Phase | Task | Effort | Dissertation Value |
|----------|-------|------|--------|-------------------|
| 🔴 HIGH | 1.3 | Framework overhead tracking | 2h | Direct: "How much overhead?" |
| 🔴 HIGH | 1.2 | Environment metadata | 4h | Direct: "Local vs GCP" |
| 🔴 HIGH | 2.2 | Reproducibility analyzer | 4h | Direct: "Repeated executions" |
| 🔴 HIGH | 2.1 | Infrastructure comparison | 5h | Direct: "Different infra" |
| 🟡 MEDIUM | 1.1 | Enhanced Trino metrics | 3h | Supporting analysis |
| 🟡 MEDIUM | 2.3 | Configuration comparison | 4h | Direct: "Different configs" |
| 🟡 MEDIUM | 3.1 | Workload classification | 5h | Direct: "Different benchmarks" |
| 🟡 MEDIUM | 4.1 | CLI commands | 6h | Usability |
| 🟢 LOW | 4.2 | Report generation | 6h | Dissertation writing |
| 🟢 LOW | 5.1 | Visualization | 5h | Dissertation figures |

---

## Recommended Implementation Order

### Week 1: Core Metrics & Infrastructure
1. ✅ Add framework overhead tracking (Phase 1.3)
2. ✅ Add Environment model and metadata (Phase 1.2)
3. ✅ Database migration

### Week 2: Analysis Engines
4. ✅ Implement ReproducibilityAnalyzer (Phase 2.2)
5. ✅ Implement InfrastructureAnalyzer (Phase 2.1)
6. ✅ Implement ConfigurationAnalyzer (Phase 2.3)

### Week 3: CLI & Integration
7. ✅ Add new CLI commands (Phase 4.1)
8. ✅ Enhanced Trino metrics capture (Phase 1.1)
9. ✅ Workload classification (Phase 3.1)

### Week 4: Reports & Polish
10. ✅ Report generation (Phase 4.2)
11. ✅ Visualization utilities (Phase 5.1)
12. ✅ Testing and documentation

---

## Database Migration Strategy

Since you're using SQLAlchemy with SQLite/PostgreSQL:

```python
# Create migration script: lib/tribench/storage/migrations/add_environment_support.py

def upgrade():
    """Add environment tracking and enhanced metrics."""
    
    # 1. Create environments table
    # 2. Add environment_id to experiments
    # 3. Add new columns to query_executions
    # 4. Backfill existing experiments with "unknown" environment
    
def downgrade():
    """Revert changes."""
    pass
```

**Alternative:** Since this is a dissertation project, consider:
- Reset database and re-run experiments with new schema
- Keep both old and new databases during transition
- Use JSON metadata column as escape hatch for new fields

---

## Success Metrics

After implementation, you should be able to run:

```bash
# Reproducibility study
tribench res analyze reproducibility exp-001 --min-runs 10
# Output: CV per query, stability score, recommended runs

# Infrastructure comparison
tribench res analyze infra exp-local exp-gcp --normalize-by cpu
# Output: Speed ratio, efficiency, cost analysis

# Framework overhead
tribench res analyze overhead exp-001
# Output: Overhead %, breakdown, comparison with raw Trino

# Configuration impact
tribench res analyze config exp-2gb exp-4gb exp-8gb --param memory
# Output: Memory vs performance curve, optimal setting

# Generate dissertation table
tribench res report comparison exp-local exp-gcp --format latex > table.tex
```

---

## Questions to Resolve

1. **GCP cost data**: Do you have access to billing APIs or will cost be manually input?
2. **Trino version**: Are you using a fixed version or comparing across versions?
3. **Historical data**: Do you need to backfill existing experiments with new metadata?
4. **Visualization output**: matplotlib inline or saved files? What format for dissertation?

---

*Last Updated: January 9, 2026*
