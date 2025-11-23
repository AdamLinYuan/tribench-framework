## Phase 1 Continued: Query Reusability Architecture (Week 5-6) ✅

### Section 1.6: Apps Directory and Query Files Feature ✅
**Completed**: Implemented apps/ directory structure and query_files loading mechanism for experiment reusability

#### Motivation

**Problem**: Inline queries in experiment YAML files led to:
- Query duplication across multiple experiments
- Difficult maintenance (fix a query bug in multiple places)
- Hard to verify queries against official TPC-H specification
- No version control tracking of query changes
- Coupling between query content and experiment configuration

**Solution**: Centralized query repository in `apps/` directory:
- Single source of truth for benchmark queries
- Separation of "what to run" (queries) from "how/where to run" (experiments)
- Easy reusability across Memory, Iceberg, different scale factors
- Clear version control and documentation

#### Implementation Components

1. **Apps Directory Structure** (`apps/`)
   - Purpose: Central repository for benchmark applications and queries
   - Structure:
     ```
     apps/
     ├── README.md              # Apps directory overview
     └── tpch/                  # TPC-H benchmark
         ├── README.md          # TPC-H query documentation
         └── queries/           # Individual SQL files
             ├── q01.sql        # Pricing Summary Report
             ├── q03.sql        # Shipping Priority
             ├── q06.sql        # Forecasting Revenue Change
             ├── q12.sql        # Shipping Modes
             ├── q14.sql        # Promotion Effect
             └── q19.sql        # Discounted Revenue
     ```
   - **Dissertation Value**: Demonstrates software architecture for reproducible research

2. **TPC-H Query Library** (6 queries implemented)
   
   **Query Selection Rationale**:
   - **Q1 (Pricing Summary)**: Pure aggregation, GROUP BY, tests columnar format benefits
   - **Q3 (Shipping Priority)**: 3-way join, ORDER BY, LIMIT - tests join optimization
   - **Q6 (Forecasting Revenue)**: Simple filter + aggregate, ideal for partition pruning
   - **Q12 (Shipping Modes)**: CASE expressions, date ranges - tests predicate pushdown
   - **Q14 (Promotion Effect)**: Pattern matching (LIKE), percentage calculation
   - **Q19 (Discounted Revenue)**: Complex OR conditions, multiple predicates
   
   **Query Characteristics**:
   - Variety: Simple aggregations to complex joins
   - Scalability: Fast (Q6) vs. compute-intensive (Q19)
   - Partition sensitivity: Some benefit from pruning (Q1, Q6), others don't (Q3)
   - Dissertation coverage: Adequate for evaluating Iceberg features

3. **ExperimentConfig Enhancement** (`lib/tribench/core/experiment.py`)
   
   **Added `query_files` field**:
   ```python
   @dataclass
   class ExperimentConfig:
       # ... existing fields ...
       query_files: List[str] = field(default_factory=list)
   ```
   
   **Updated `from_yaml()` method**:
   - Added `cli_overrides` parameter for runtime configuration
   - Normalizes query_files to list format (accepts string or list)
   - Applies CLI overrides after YAML load
   
   **Helper function**:
   ```python
   def normalize_to_list(value):
       """Convert string or list to list, handle None."""
       if value is None:
           return []
       if isinstance(value, str):
           return [value]
       return list(value)
   ```

4. **TrinoExperiment Query Loading** (`lib/tribench/experiments/trino_experiment.py`)
   
   **Enhanced `_collect_queries()` method**:
   - **Multi-strategy path resolution**:
     - Strategy 1: Relative to project root (supports `apps/tpch/queries/q01.sql`)
     - Strategy 2: Relative to experiments/ directory (for convenience)
     - Absolute paths supported
   - **File loading**:
     - Reads SQL content with `query_path.read_text()`
     - Creates query dict: `{name: query_path.stem, sql: sql_content, source: str(query_path)}`
   - **Error handling**:
     - Logs successful file loads
     - Detailed error messages with all attempted paths
     - Raises FileNotFoundError with context
   
   **Backward compatibility**:
   - Inline queries from `queries:` list still work
   - Both inline and query_files can coexist in same experiment
   - No breaking changes to existing experiments

#### Usage Examples

**Before (Inline Query)**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml
name: "tpch-q1-memory-sf1"
queries:
  - |
    SELECT
        l_returnflag,
        l_linestatus,
        sum(l_quantity) as sum_qty,
        sum(l_extendedprice) as sum_base_price,
        sum(l_extendedprice * (1 - l_discount)) as sum_disc_price,
        sum(l_extendedprice * (1 - l_discount) * (1 + l_tax)) as sum_charge,
        avg(l_quantity) as avg_qty,
        avg(l_extendedprice) as avg_price,
        avg(l_discount) as avg_disc,
        count(*) as count_order
    FROM
        lineitem
    WHERE
        l_shipdate <= date '1998-12-01' - interval '90' day
    GROUP BY
        l_returnflag,
        l_linestatus
    ORDER BY
        l_returnflag,
        l_linestatus
```

**After (Query File Reference)**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml
name: "tpch-q1-memory-sf1"
query_files: ["apps/tpch/queries/q01.sql"]
connection:
  catalog: "memory"
  schema: "default"
```

**Multiple Experiments, Same Query**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml (Memory connector)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "memory", schema: "tpch_sf1"}

# experiments/tpch-q1-iceberg-sf1.yaml (Iceberg connector)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "iceberg", schema: "tpch_sf1"}

# experiments/tpch-q1-iceberg-sf10.yaml (Different scale factor)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "iceberg", schema: "tpch_sf10"}
```

#### Testing & Validation

**End-to-End Test**:
```bash
# Load dataset
tribench data load tpch-tiny --catalog memory --schema default

# Run experiment with query_files
tribench exp run experiments/tpch-q1-memory-sf1.yaml

# Output:
# Loading experiment: tpch-q1-memory-sf1.yaml
# Experiment: tpch-q1-memory-sf1
# Loaded query from file: apps/tpch/queries/q01.sql
# ✓ Preparation complete
# Connected to Trino at localhost:8080
# Prepared 1 queries for execution
# 
# Measured run 1/3: q01_run1 - Query completed in 0.13s, returned 4 rows
# Measured run 2/3: q01_run2 - Query completed in 0.13s, returned 4 rows
# Measured run 3/3: q01_run3 - Query completed in 0.10s, returned 4 rows
# 
# ✓ Execution complete
# Success rate: 100.0%
# Execution time (mean): 0.122s
# ✓ Validation passed
# Results saved to: results/tpch-q1-memory-sf1_20251019_233827.json
```

**Query File Loading Verification**:
- ✅ Path resolution works from project root
- ✅ SQL content loaded correctly
- ✅ Query name extracted from filename (q01.sql → q01)
- ✅ Source tracked for debugging
- ✅ Multiple query files supported in same experiment

**Schema Configuration Fix**:
- Initial issue: Pointed to `memory.benchmarks` schema (didn't exist)
- Data actually loaded to `memory.default` schema
- Fixed experiment configs to use `schema: "default"`
- Validated with 100% success rate

#### Documentation Created

1. **apps/README.md**
   - Purpose and benefits of apps directory
   - Structure and organization
   - Usage examples (before/after)
   - Getting started guide
   - Current status (6 queries implemented)

2. **apps/tpch/README.md**
   - TPC-H query characteristics table
   - Query selection rationale for dissertation
   - Expected results for each query
   - Performance considerations
   - Validation instructions
   - References to TPC-H specification

3. **Query File Headers**
   - Each .sql file includes:
     - Query number and name
     - Description of purpose
     - Expected result format
     - SQL implementation

#### Benefits Achieved

1. **Reusability** ✅
   - Same query runs on Memory, Iceberg, different scale factors
   - No duplication across 10+ planned experiment variants
   - Query changes propagate automatically

2. **Maintainability** ✅
   - Fix query once in apps/tpch/queries/
   - All experiments benefit immediately
   - Clear version control history

3. **Verification** ✅
   - Easy to compare against official TPC-H specification
   - Query validation against Trino built-in TPC-H catalog
   - Documentation tracks expected results

4. **Research Workflow** ✅
   - Dissertation experiments require same query on different systems
   - Query_files enables systematic comparison
   - Clean separation: queries (what) vs experiments (how/where)

5. **Extensibility** ✅
   - Easy to add remaining 16 TPC-H queries
   - Structure supports TPC-DS queries (apps/tpcds/)
   - Custom benchmark queries supported

#### Dissertation Contributions

1. **Software Architecture**:
   - Demonstrates separation of concerns
   - Reusable component design
   - Version control best practices

2. **Reproducible Research**:
   - Queries documented and version-controlled
   - Same query definition across all experiments
   - No human error from copy-paste

3. **Systematic Evaluation**:
   - Enables fair comparison across systems
   - Identical queries ensure apples-to-apples comparison
   - Query characteristics table guides experiment design

4. **Framework Quality**:
   - Professional software engineering practices
   - Clear documentation for future users
   - Extensible for follow-on research

#### Files Created/Modified

**New Files**:
- `apps/README.md` - Apps directory overview and usage guide
- `apps/tpch/README.md` - TPC-H query documentation
- `apps/tpch/queries/q01.sql` - Pricing Summary Report Query
- `apps/tpch/queries/q03.sql` - Shipping Priority Query
- `apps/tpch/queries/q06.sql` - Forecasting Revenue Change Query
- `apps/tpch/queries/q12.sql` - Shipping Modes Query
- `apps/tpch/queries/q14.sql` - Promotion Effect Query
- `apps/tpch/queries/q19.sql` - Discounted Revenue Query
- `experiments/tpch-q1-memory-sf1.yaml` - Example using query_files

**Modified Files**:
- `lib/tribench/core/experiment.py` - Added query_files field, cli_overrides, normalize_to_list()
- `lib/tribench/experiments/trino_experiment.py` - Enhanced _collect_queries() with file loading
- `experiments/tpch-q1-custom-dataset.yaml` - Fixed schema configuration

#### Technical Challenges Solved

1. **Path Resolution**:
   - Challenge: Relative paths ambiguous (from where?)
   - Solution: Multi-strategy resolution (project root first, then experiments/)
   - Result: Flexible path specification

2. **Backward Compatibility**:
   - Challenge: Don't break existing inline queries
   - Solution: Support both queries and query_files simultaneously
   - Result: Zero breaking changes

3. **Schema Configuration**:
   - Challenge: Mismatch between data location and experiment config
   - Solution: Updated configs to point to correct schema
   - Result: 100% success rate on loaded data

4. **CLI Override Support**:
   - Challenge: CLI needs to override YAML parameters
   - Solution: Added cli_overrides parameter to from_yaml()
   - Result: Runtime configuration flexibility

#### Lessons Learned

1. **Apps Folder Value**:
   - Initial skepticism: "Is apps/ necessary?"
   - Reality: Critical for query reuse across 10+ experiments
   - Insight: Centralization reduces duplication and errors

2. **Path Resolution Strategy**:
   - Single strategy insufficient (what's "relative"?)
   - Multiple strategies provide flexibility
   - Detailed error messages essential for debugging

3. **Schema Naming**:
   - Assumption: Data loaded to "benchmarks" schema
   - Reality: Data in "default" schema
   - Lesson: Always verify data location before experiments

4. **Backward Compatibility**:
   - Supporting both old and new patterns increases adoption
   - Deprecation warnings guide users to new approach
   - No rush to remove old functionality

#### Future Enhancements


### Time Investment

- **Apps Directory Design**: 1 hour (structure, README planning)
- **TPC-H Query Implementation**: 2 hours (6 queries with documentation)
- **ExperimentConfig Enhancement**: 1 hour (query_files field, normalize_to_list, cli_overrides)
- **TrinoExperiment File Loading**: 2 hours (path resolution, error handling, testing)
- **Documentation**: 1.5 hours (apps/README.md, apps/tpch/README.md, query headers)
- **Testing & Validation**: 1.5 hours (end-to-end workflow, schema config fix)
- **Journal Documentation**: 1 hour (this section)
- **Total**: ~10 hours for query reusability architecture

---

*Last Updated: 19 October 2025*
*Total Development Time: ~88.5 hours*
*Phase 0 Complete | Phase 1 Complete (Sections 1.1-1.6)*
---

## Bug Fix: Result File Overwriting Issue (20 October 2025) ✅

### Problem Discovery

**Issue**: When running experiments with multiple queries (e.g., `tpch-q1-memory-tiny.yaml` with 22 queries), only the last 2 queries produced result files instead of all 22.

**Symptom**: 
- Expected: 22 result files (1 per query × 1 run)
- Actual: 2 result files (only q19 and q22)
- All queries executed successfully (100% success rate)

**Root Cause Analysis**:
```bash
# Log output showed all saves to same filename:
Saved result to: .../results/tpch-q1-memory-tiny_20251020_095619.json
Saved result to: .../results/tpch-q1-memory-tiny_20251020_095619.json
Saved result to: .../results/tpch-q1-memory-tiny_20251020_095619.json
# ... (20 more times)
```

**Diagnosis**: 
- Filename generation used `%Y%m%d_%H%M%S` format (seconds precision)
- All 22 queries executed within the **same second**
- Identical timestamps → identical filenames → file overwriting
- Only last query result (q22) survived

### Solution Implemented

**File**: `lib/tribench/experiments/result_collector.py` (line 133)

**Changes**:
1. **Added microsecond precision** to timestamps (`%Y%m%d_%H%M%S_%f`)
2. **Added query name and run number** to filename for uniqueness
3. **Enhanced filename generation logic**:

```python
# Before (buggy):
timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
filename = f"{result.experiment_name}_{timestamp_str}.json"

# After (fixed):
timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S_%f")

# Add query name and run number if available
query_name = result.metadata.get("query_name", "")
run_number = result.metadata.get("run_number", "")

if query_name and run_number:
    filename = f"{result.experiment_name}_{query_name}_run{run_number}_{timestamp_str}.json"
elif query_name:
    filename = f"{result.experiment_name}_{query_name}_{timestamp_str}.json"
else:
    filename = f"{result.experiment_name}_{timestamp_str}.json"
```

### Verification

**Test Run**:
```bash
tribench exp run experiments/tpch-q1-memory-tiny.yaml
```

**Results**:
```
Saved result to: .../tpch-q1-memory-tiny_q01_run1_20251020_095722_421564.json
Saved result to: .../tpch-q1-memory-tiny_q02_run1_20251020_095722_479100.json
Saved result to: .../tpch-q1-memory-tiny_q03_run1_20251020_095722_513803.json
...
Saved result to: .../tpch-q1-memory-tiny_q22_run1_20251020_095723_293192.json
```

✅ **All 22 result files created successfully**

**New Filename Format**:
- Pattern: `{experiment}_{query}_{run}_{timestamp_with_microseconds}.json`
- Example: `tpch-q1-memory-tiny_q01_run1_20251020_095722_421564.json`
- Benefits:
  - Unique even for fast-executing queries (< 1 second)
  - Human-readable query identification
  - Chronological ordering maintained
  - Run number tracking built-in

### Impact

**Before Fix**:
- ❌ Only 1 result file per second of execution
- ❌ Silent data loss (overwritten files)
- ❌ Incomplete experiment results
- ❌ False impression of query failures

**After Fix**:
- ✅ Every query execution saves unique result
- ✅ No data loss from overwriting
- ✅ Complete experiment results (22/22 files)
- ✅ Better file organization by query name

### Lessons Learned

1. **Timestamp Precision Matters**:
   - Seconds precision insufficient for fast queries
   - Microseconds (6 decimal places) provide adequate uniqueness
   - Modern systems can execute 10+ queries per second

2. **Semantic Filenames**:
   - Including query name makes results self-documenting
   - Run number enables easy identification of repeated runs
   - Better than pure timestamp-based naming

3. **Silent Failures Are Dangerous**:
   - File overwrites don't generate errors
   - Need to verify file count matches expected output
   - Consider logging warning when overwriting existing file

4. **Integration Testing Reveals Real Issues**:
   - Unit tests wouldn't catch this (no real filesystem operations)
   - End-to-end testing with realistic workloads essential
   - Performance characteristics affect correctness

### Dissertation Relevance

**Software Quality**:
- Demonstrates importance of thorough testing
- Real-world usage reveals edge cases
- User feedback drives quality improvements

**Research Reproducibility**:
- Data loss bug would invalidate experimental results
- Complete result collection essential for statistical analysis
- File naming impacts result organization and analysis workflow

**Performance Considerations**:
- Fast query execution (< 1s) created the collision
- Framework must handle high-throughput scenarios
- Trino's performance creates edge cases for benchmarking tools

### Time Investment

- **Bug Investigation**: 0.25 hours (examining logs, understanding root cause)
- **Solution Implementation**: 0.25 hours (code changes, enhanced filename logic)
- **Testing & Verification**: 0.25 hours (re-running experiment, verifying all files)
- **Documentation**: 0.25 hours (journal update)
- **Total**: ~1 hour

---

