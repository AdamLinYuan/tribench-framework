# Advanced Query Metrics - January 2026

**Date:** January 9, 2026  
**Phase:** Dissertation Analysis Support  
**Status:** ✅ Completed

## Overview

Enhanced query metrics collection to support detailed dissertation analysis. Implemented high and medium priority metrics for understanding query performance, memory pressure, parallelism, and query plan behavior.

## Problem Statement

Basic metrics (execution time, rows returned) insufficient for dissertation research:
- No visibility into query planning overhead
- Can't analyze memory pressure (spilling)
- Missing parallelism insights (splits, tasks)
- No query plan regression detection
- Limited stage-level performance data

## Solution

Comprehensive metrics enhancement using Trino REST API and cursor statistics to capture detailed query execution metadata.

## Implementation Details

### HIGH PRIORITY Metrics

#### 1. Planning/Analysis Time Breakdown
**Purpose:** Understand query compilation overhead

**Implementation:**
- Enhanced `QueryExecution` model with timing columns
- Integrated `TrinoAPIClient` to fetch breakdown from REST API
- Added `_enrich_query_metadata()` method in `TrinoExperiment`
- Timing stored: `planning_time_ms`, `analysis_time_ms`, `execution_time_ms`

**Database Schema:**
```sql
ALTER TABLE query_execution ADD COLUMN planning_time_ms REAL;
ALTER TABLE query_execution ADD COLUMN analysis_time_ms REAL;
```

#### 2. Spill Metrics
**Purpose:** Memory pressure analysis for Iceberg queries

**Implementation:**
- Added `spilled_bytes` column (BIGINT, nullable)
- Captured from `cursor.stats['spilledBytes']`
- Updated storage layer to persist spill data

**Use Case:**
```python
# Analyze memory pressure
high_spill_queries = [
    q for q in results 
    if q['spilled_bytes'] > 1_000_000_000  # >1GB spilled
]
```

#### 3. Stage-Level Metrics
**Purpose:** Query optimization insights

**Implementation:**
- Integrated `TrinoAPIClient.get_stage_metrics(query_id)`
- Stage data stored in `query_metadata` JSON column
- Aggregated `total_tasks` from stage data
- Per-stage metrics: tasks, memory, CPU, I/O

**Captured Metrics:**
- Total/running/completed tasks per stage
- Memory allocation per stage
- CPU time per stage
- Input/output data per stage

### MEDIUM PRIORITY Metrics

#### 4. Split/Task Counts
**Purpose:** Parallelism analysis

**Implementation:**
- Added columns: `total_splits`, `completed_splits`, `total_tasks`
- Captured from `cursor.stats`
- Aggregated task count from stage metrics

**Database Schema:**
```sql
ALTER TABLE query_execution ADD COLUMN total_splits INTEGER;
ALTER TABLE query_execution ADD COLUMN completed_splits INTEGER;
ALTER TABLE query_execution ADD COLUMN total_tasks INTEGER;
```

**Analysis Use:**
```python
# Calculate parallelism efficiency
efficiency = completed_splits / total_splits
avg_tasks_per_query = sum(total_tasks) / len(queries)
```

#### 5. Query Plan Hash
**Purpose:** Detect plan regressions across runs

**Implementation:**
- Added `query_plan_hash` column (VARCHAR(64))
- Computed SHA256 hash of logical plan
- Fetched via Trino API `explain` endpoint
- Stored for comparison across experiments

**Use Case:**
```python
# Detect plan changes
if run1_hash != run2_hash:
    logger.warning(f"Query plan changed for {query_name}")
```

## Technical Architecture

### Metrics Collection Flow

```
Query Execution
    ↓
1. Execute via cursor.execute()
    ↓
2. Capture cursor.stats (basic metrics)
    ↓
3. Call TrinoAPIClient.get_query_info(query_id)
    ↓
4. Extract planning/analysis times
    ↓
5. Call TrinoAPIClient.get_stage_metrics(query_id)
    ↓
6. Aggregate stage-level data
    ↓
7. Compute query plan hash
    ↓
8. Store all metrics to database
```

### Code Changes

**Files Modified:**
- `lib/tribench/storage/models.py` - Database schema
- `lib/tribench/query/query_executor.py` - Cursor stats capture
- `lib/tribench/experiments/trino/experiment.py` - API integration
- `lib/tribench/storage/result/query_store.py` - Metric persistence
- `lib/tribench/monitoring/trino/api_client.py` - API endpoints

## Results

### Database Schema Updates

**New Columns in `query_execution`:**
```sql
planning_time_ms      REAL
analysis_time_ms      REAL
spilled_bytes         BIGINT
total_splits          INTEGER
completed_splits      INTEGER
total_tasks           INTEGER
query_plan_hash       VARCHAR(64)
```

**Existing JSON Column Enhanced:**
- `query_metadata` - Now includes stage-level metrics

### Metrics Available for Analysis

1. **Timing Breakdown:**
   - Planning time (query compilation)
   - Analysis time (semantic analysis)
   - Execution time (actual query run)

2. **Memory Metrics:**
   - Peak memory usage
   - Spilled bytes (disk overflow)
   - Per-stage memory allocation

3. **Parallelism Metrics:**
   - Total splits generated
   - Completed splits
   - Total tasks executed
   - Tasks per stage

4. **Query Plans:**
   - Logical plan hash
   - Stage breakdown
   - Plan stability across runs

## CLI Enhancements

### View Advanced Metrics

```bash
# Show detailed query metrics
tribench res queries <run_id>

# Show specific query with plan hash
tribench res queries <run_id> --query q01 --show-hash

# Summary statistics
tribench res queries <run_id> --summary

# JSON export for analysis
tribench res queries <run_id> --format json > metrics.json
```

### Sample Output

```
Advanced Metrics:
──────────────────────────────────────────────────────────────────────────
Query      Plan Time    Analyze Time   Splits (C/T)    Tasks   Spilled Bytes
──────────────────────────────────────────────────────────────────────────
q01        125.50ms     45.30ms        128/128         16      0B
q09        892.10ms     156.20ms       512/512         64      2,147,483,648B
q17        234.67ms     89.45ms        256/256         32      0B
──────────────────────────────────────────────────────────────────────────
```

## Validation

### Testing Strategy
1. ✅ Unit tests for API client methods
2. ✅ Integration tests with real Trino cluster
3. ✅ Database migration tests
4. ✅ Backward compatibility (nullable columns)

### Verified Scenarios
- Queries with no spilling
- Queries with heavy spilling (>1GB)
- Single-stage vs multi-stage queries
- Plan hash stability across identical runs
- Plan hash changes with different data

## Performance Impact

**Overhead Analysis:**
- API calls add ~50-100ms per query
- Negligible for queries >1s execution time
- Stage metrics API most expensive (~40ms)
- Plan hash computation ~10ms

**Mitigation:**
- API calls only for successful queries
- Parallel execution unaffected
- Metrics optional (can disable API enrichment)

## Use Cases for Dissertation

### 1. Memory Pressure Analysis
```sql
SELECT query_name, AVG(spilled_bytes) as avg_spill
FROM query_execution
WHERE format = 'iceberg'
GROUP BY query_name
HAVING avg_spill > 0;
```

### 2. Parallelism Efficiency
```sql
SELECT query_name, 
       AVG(completed_splits * 1.0 / total_splits) as split_efficiency,
       AVG(total_tasks) as avg_parallelism
FROM query_execution
GROUP BY query_name;
```

### 3. Query Optimization Overhead
```sql
SELECT query_name,
       AVG(planning_time_ms + analysis_time_ms) as compilation_time,
       AVG(execution_time_ms) as run_time,
       AVG(planning_time_ms + analysis_time_ms) * 100.0 / 
           AVG(execution_time_ms) as overhead_pct
FROM query_execution
GROUP BY query_name;
```

### 4. Plan Stability
```sql
SELECT query_name, COUNT(DISTINCT query_plan_hash) as plan_variations
FROM query_execution
GROUP BY query_name
HAVING plan_variations > 1;
```

## Related Documentation

- Implementation details: `docs/ADVANCED_METRICS_IMPLEMENTATION.md`
- API client: `lib/tribench/monitoring/trino/api_client.py`
- CLI usage: `tribench res queries --help`

## Lessons Learned

1. **Trino REST API is powerful** - Provides metrics not in cursor stats
2. **JSON columns flexible** - Good for evolving metrics
3. **Nullable columns essential** - Backward compatibility
4. **Hashing helps regression detection** - Query plans can silently change
5. **Stage metrics most valuable** - Shows bottlenecks clearly

## Future Enhancements

Potential future additions:
- [ ] Network I/O metrics per stage
- [ ] Resource wait times
- [ ] Operator-level statistics
- [ ] Cost-based optimizer metrics
- [ ] Adaptive query execution data
