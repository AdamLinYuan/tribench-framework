# Advanced Query Metrics Implementation Summary

**Date**: January 9, 2026  
**Status**: ✅ Completed

## Overview

Implemented high and medium priority metrics capture enhancements to support dissertation analysis requirements. These changes enable detailed query performance analysis, memory pressure monitoring, parallelism insights, and query plan regression detection.

## Tasks Completed

### ✅ HIGH PRIORITY

#### 1. Store Planning/Analysis Time Breakdown
- **Value**: Understanding query compilation overhead
- **Implementation**:
  - Enhanced `QueryExecution` model with existing `planning_time_ms`, `analysis_time_ms`, `execution_time_ms` columns
  - Added API client integration to fetch detailed timing breakdown from Trino REST API
  - Implemented `_enrich_query_metadata()` method in `TrinoExperiment` to call API after query execution
  - Updated storage layer to extract and save timing metrics to database

#### 2. Add Spill Metrics
- **Value**: Memory pressure analysis for Iceberg
- **Implementation**:
  - Added `spilled_bytes` column to `QueryExecution` model (BIGINT, nullable)
  - Updated `query_executor.py` to capture `spilledBytes` from `cursor.stats`
  - Updated storage layer to extract and persist spill metrics
  - Added to query store retrieval dictionary

#### 3. Fetch and Store Stage-Level Metrics
- **Value**: Query optimization insights
- **Implementation**:
  - Integrated `TrinoAPIClient.get_stage_metrics()` call in query execution flow
  - Stage metrics stored in `query_metadata` JSON column (includes per-stage tasks, memory, CPU, data metrics)
  - Aggregated `total_tasks` from stage data and stored as top-level column
  - Provides detailed breakdown: total_tasks, running_tasks, completed_tasks, memory, CPU, I/O per stage

### ✅ MEDIUM PRIORITY

#### 4. Add Split/Task Counts
- **Value**: Parallelism analysis
- **Implementation**:
  - Added columns: `total_splits` (INTEGER), `completed_splits` (INTEGER), `total_tasks` (INTEGER)
  - Captured from `cursor.stats`: `totalSplits`, `completedSplits`
  - Captured `total_tasks` from aggregated stage metrics via API
  - Updated storage and query store layers

#### 5. Store Query Plan Hash
- **Value**: Detecting plan regressions
- **Implementation**:
  - Added `query_plan_hash` column (VARCHAR(64), nullable) to `QueryExecution` model
  - Integrated `TrinoAPIClient.get_query_plan()` call to fetch full query plan
  - Calculate SHA256 hash of plan JSON (sorted keys for consistency)
  - Store both hash (for regression detection) and full plan (in metadata for detailed analysis)

### ⏸️ LOW PRIORITY (Deferred)

#### 6. Add Iceberg-Specific Metadata Tracking
- **Status**: Not implemented (can be added later when needed)
- **Value**: Advanced lakehouse analysis
- **Future work**: Iceberg snapshot IDs, manifest counts, file stats

## Files Modified

### Schema Changes
1. **lib/tribench/storage/models.py**
   - Added `spilled_bytes: Column(BigInteger, nullable=True)`
   - Added `total_splits: Column(Integer, nullable=True)`
   - Added `completed_splits: Column(Integer, nullable=True)`
   - Added `total_tasks: Column(Integer, nullable=True)`
   - Added `query_plan_hash: Column(String(64), nullable=True)`

### Metrics Capture
2. **lib/tribench/experiments/query_executor.py**
   - Enhanced `execute_query()` to capture `spilled_bytes`, `total_splits`, `completed_splits` from `cursor.stats`

### API Integration
3. **lib/tribench/experiments/trino/experiment.py**
   - Added import for `TrinoAPIClient` with availability check
   - Initialize API client in `__init__()` using connection config
   - Added `_enrich_query_metadata()` method to fetch:
     - Planning/analysis/execution time breakdown
     - Stage-level metrics (tasks, memory, CPU, I/O)
     - Query plan and calculated hash (SHA256)
   - Integrated enrichment call in `_execute_single_query()` after query execution

### Storage Layer
4. **lib/tribench/experiments/trino/storage.py**
   - Enhanced `_save_query_execution()` to extract and pass new metrics:
     - Planning/analysis timing
     - Spill metrics
     - Split/task counts
     - Query plan hash
   - All metrics passed as `**metrics` kwargs to `add_query_execution()`

5. **lib/tribench/storage/result/query_store.py**
   - Updated `get_run_query_executions()` dictionary to include:
     - `spilled_bytes`
     - `total_splits`, `completed_splits`, `total_tasks`
     - `query_plan_hash`

### Migration
6. **utils/migrations/001_add_advanced_query_metrics.py** (NEW)
   - Migration script to add new columns to existing databases
   - Supports SQLite and PostgreSQL
   - Safe execution: checks for existing columns before adding

## Database Schema Changes

```sql
-- New columns added to query_executions table
ALTER TABLE query_executions ADD COLUMN spilled_bytes BIGINT;
ALTER TABLE query_executions ADD COLUMN total_splits INTEGER;
ALTER TABLE query_executions ADD COLUMN completed_splits INTEGER;
ALTER TABLE query_executions ADD COLUMN total_tasks INTEGER;
ALTER TABLE query_executions ADD COLUMN query_plan_hash VARCHAR(64);
```

## Metrics Flow

### Before (cursor.stats only)
```
Query Execution → cursor.stats → {query_id, cpu_time_ms, processed_rows, ...}
                                    ↓
                              Save to database (limited metrics)
```

### After (cursor.stats + API enrichment)
```
Query Execution → cursor.stats → {query_id, cpu_time_ms, spilled_bytes, total_splits, ...}
                      ↓
                 API Enrichment → {planning_time_ms, analysis_time_ms, stage_metrics, query_plan_hash}
                      ↓
                 Save to database (comprehensive metrics)
```

## Metrics Captured Summary

| Metric | Source | Priority | Column | Purpose |
|--------|--------|----------|--------|---------|
| **Planning Time** | API | HIGH | `planning_time_ms` | Query compilation overhead |
| **Analysis Time** | API | HIGH | `analysis_time_ms` | Semantic analysis overhead |
| **Execution Time** | API | HIGH | `execution_time_ms` | Pure execution time |
| **Spilled Bytes** | cursor.stats | HIGH | `spilled_bytes` | Memory pressure indicator |
| **Total Splits** | cursor.stats | MEDIUM | `total_splits` | Parallelism degree |
| **Completed Splits** | cursor.stats | MEDIUM | `completed_splits` | Parallelism efficiency |
| **Total Tasks** | API (aggregated) | MEDIUM | `total_tasks` | Query complexity |
| **Query Plan Hash** | API (calculated) | MEDIUM | `query_plan_hash` | Plan regression detection |
| **Stage Metrics** | API | HIGH | `metadata.stage_metrics` | Per-stage analysis |
| **Full Query Plan** | API | MEDIUM | `metadata.query_plan` | Detailed optimization analysis |

## Usage Example

### For New Databases
New databases will automatically include all columns when initialized via `init_database()`.

### For Existing Databases
Run the migration script:
```bash
# Default database (SQLite in results/tribench.db)
python utils/migrations/001_add_advanced_query_metrics.py

# Custom database
TRIBENCH_DATABASE_URL=postgresql://user:pass@host/dbname \
  python utils/migrations/001_add_advanced_query_metrics.py
```

### Accessing New Metrics
```python
from tribench.storage import ResultStorage

storage = ResultStorage()

# Get query executions with new metrics
query_execs = storage.get_run_query_executions(run_id=1)

for qe in query_execs:
    print(f"Query: {qe['query_name']}")
    print(f"  Planning time: {qe['planning_time_ms']}ms")
    print(f"  Spilled: {qe['spilled_bytes']} bytes")
    print(f"  Splits: {qe['completed_splits']}/{qe['total_splits']}")
    print(f"  Tasks: {qe['total_tasks']}")
    print(f"  Plan hash: {qe['query_plan_hash']}")
```

## Dissertation Value

These metrics enable comprehensive analysis for your dissertation comparisons:

1. **Local vs GCP Infrastructure**
   - Compare spill rates (memory pressure differences)
   - Analyze parallelism differences (splits, tasks)
   - Detect plan changes across environments

2. **Framework Overhead**
   - Separate planning/analysis time from execution time
   - Measure framework initialization vs query execution

3. **Repeated Executions**
   - Track plan stability via plan hash
   - Analyze variance in spill/parallelism metrics

4. **Configuration Comparison**
   - Compare parallelism efficiency across worker counts
   - Analyze memory pressure under different configurations

5. **Benchmark Analysis**
   - Identify memory-intensive queries (high spill)
   - Classify queries by parallelism characteristics
   - Detect query plan regressions

## Testing Recommendations

1. **Verify Metrics Capture**: Run a test experiment and check all metrics are populated
2. **API Availability**: Test with and without API access (graceful degradation)
3. **Migration**: Test migration script on copy of production database
4. **Analysis Queries**: Create test queries using new metrics for dissertation analysis

## Next Steps

Based on the improvement plan, consider implementing:

1. **Phase 1 (Remaining)**: Framework overhead tracking (measure Python time vs Trino time)
2. **Phase 1 (Remaining)**: Environment metadata model (track infra details for local vs GCP)
3. **Phase 2**: New analyzers (Infrastructure, Reproducibility, Configuration comparison)
4. **Phase 3**: Benchmark categorization using captured metrics
5. **Phase 4**: CLI enhancements for new comparison capabilities

## Notes

- All changes are backward compatible (nullable columns, graceful API failures)
- API enrichment is optional - framework works without it (reduced metrics)
- Stage metrics stored in JSON for flexibility in future analysis
- Query plan stored in metadata JSON to avoid large column storage
- Migration script is idempotent (can be run multiple times safely)
