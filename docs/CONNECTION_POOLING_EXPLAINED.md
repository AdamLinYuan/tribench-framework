# Connection Pooling & Parallel Execution Explained

## Overview

Connection pooling enables efficient concurrent query execution by reusing database connections across multiple threads, eliminating the overhead of creating new connections for each query.

## Architecture

### Components

1. **ConnectionPool** (`lib/tribench/config/connection.py`)
   - Thread-safe pool of Trino database connections
   - Manages connection lifecycle (create, acquire, release, close)
   - Uses `queue.Queue` for thread-safe connection distribution

2. **QueryExecutor** (`lib/tribench/experiments/query_executor.py`)
   - Executes queries using connections from the pool
   - Method: `execute_with_pool(query, pool, fetch_results)`

3. **TrinoExperiment** (`lib/tribench/experiments/trino_experiment.py`)
   - Orchestrates parallel execution
   - Creates and manages the connection pool
   - Uses `ThreadPoolExecutor` for parallel query execution

## How It Works

### 1. Pool Initialization (Eager Mode)

When parallel execution starts:

```
┌─────────────────────────────────────────────────┐
│ TrinoExperiment._execute_queries_parallel()    │
│                                                 │
│ if self._connection_pool is None:              │
│   pool_size = max_workers                      │
│   self._connection_pool = ConnectionPool(      │
│     config, pool_size, eager_create=True       │
│   )                                             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ ConnectionPool.__init__() with eager_create=True     │
│                                                      │
│ For i in range(pool_size):                          │
│   conn = config.connect()  # Create Trino connection│
│   _pool.put(conn)         # Add to available queue  │
│   _all_connections.append(conn)                     │
└──────────────────────────────────────────────────────┘

Result: All connections pre-created and ready
```

**Example**: If `max_workers=4`, pool creates 4 Trino connections immediately.

### 2. Parallel Query Execution

```
┌────────────────────────────────────────────────┐
│ ThreadPoolExecutor (max_workers=4)             │
│                                                │
│  Thread 1   Thread 2   Thread 3   Thread 4    │
│     │          │          │          │         │
│     ▼          ▼          ▼          ▼         │
│  execute_query_task() for each query          │
└────────────────┬───────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│ QueryExecutor.execute_with_pool(query, pool)        │
│                                                      │
│ 1. with pool.acquire() as conn:  ← Get connection   │
│ 2.   cursor = conn.cursor()                         │
│ 3.   cursor.execute(query)                          │
│ 4.   rows = cursor.fetchall()                       │
│ 5.   # Connection auto-released on exit             │
└──────────────────────────────────────────────────────┘
```

### 3. Connection Acquisition Flow

```
Thread requests connection via pool.acquire()
                │
                ▼
┌───────────────────────────────────────────────┐
│ ConnectionPool.get_connection()               │
│                                               │
│ Try to get from queue (non-blocking):        │
│   conn = _pool.get(block=False)              │
└────┬──────────────────────────────────┬──────┘
     │                                   │
  SUCCESS                              EMPTY
     │                                   │
     ▼                                   ▼
Return conn                    ┌─────────────────────────┐
immediately                    │ Pool is full?           │
                              │ (created >= pool_size)  │
                              └───┬──────────────┬──────┘
                                  │              │
                                 NO             YES
                                  │              │
                                  ▼              ▼
                      ┌──────────────────┐  Wait for release:
                      │ Create new conn  │  conn = _pool.get(
                      │ (outside lock)   │    block=True,
                      │ Add to pool      │    timeout=30.0
                      └──────────────────┘  )
```

### 4. Connection Release Flow

```
Query completes or errors
        │
        ▼
┌──────────────────────────────────────────┐
│ pool.acquire() context manager exits     │
│                                          │
│ finally:                                 │
│   pool.release_connection(conn)          │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ ConnectionPool.release_connection()      │
│                                          │
│ _pool.put(conn, block=False)            │
│ _released_count += 1                     │
└──────────────────────────────────────────┘

Connection now available for other threads
```

## Example Execution Timeline

**Scenario**: 10 queries, 4 workers, pool size = 4

```
Time   Thread1    Thread2    Thread3    Thread4    Pool Status
────   ───────    ───────    ───────    ───────    ───────────
0ms    Init pool (create 4 connections)            [C1,C2,C3,C4]
       
10ms   Q1←C1      Q2←C2      Q3←C3      Q4←C4      []
       (query 1)  (query 2)  (query 3)  (query 4)  
       
500ms  Q1 done    Q2 done    Q3 running Q4 running [C1,C2]
       Q5←C1      Q6←C2                             []
       (query 5)  (query 6)
       
1000ms Q5 running Q6 running Q3 done    Q4 done    [C3,C4]
                             Q7←C3      Q8←C4      
                             (query 7)  (query 8)  []
       
1500ms Q5 done    Q6 done    Q7 running Q8 running [C1,C2]
       Q9←C1      Q10←C2                            []
       (query 9)  (query 10)
       
2000ms Q9 done    Q10 done   Q7 done    Q8 done    [C1,C2,C3,C4]
       Done       Done       Done       Done
```

**Key Insight**: With 10 queries and 4 workers:
- Only 4 connections created (not 10!)
- Connections reused across multiple queries
- Maximum parallelism = 4 concurrent queries

## Performance Characteristics

### Eager Creation (Current Implementation)

**Advantages**:
- ✅ All connections ready upfront (no creation delay during execution)
- ✅ Predictable performance (no mid-execution pauses)
- ✅ Maximum parallelism from first query
- ✅ No lock contention during query execution

**Trade-offs**:
- ⚠️  Higher startup time (creates all connections at pool init)
- ⚠️  Uses all connections even if not all workers run simultaneously

### Why Eager is Better for Benchmarking

```
Lazy Creation:
Pool Init (0ms) → Q1,Q2,Q3,Q4 start → Create C1,C2,C3,C4 (200ms) → Execute
Total: 200ms overhead

Eager Creation:
Pool Init & Create C1,C2,C3,C4 (200ms) → Q1,Q2,Q3,Q4 start → Execute
Total: 200ms upfront, 0ms overhead during benchmark
```

For benchmarking, we want:
- **Consistent timing** - no creation delays during measured runs
- **Repeatability** - same conditions for each run
- **Isolation** - connection setup cost separate from query execution

## Thread Safety

### Thread-Safe Components

1. **queue.Queue** (`_pool`)
   - Built-in thread-safe queue for available connections
   - Handles concurrent get/put operations

2. **threading.Lock** (`_lock`)
   - Protects shared state (_all_connections, counters)
   - Used minimally to avoid contention

3. **Context Manager** (`pool.acquire()`)
   - Guarantees connection release (even on exception)
   - RAII pattern for resource management

### Critical Sections

```python
# Only held during state updates (fast operations)
with self._lock:
    if self._created_count < self.pool_size:
        self._created_count += 1  # Reserve slot
        # Release lock before network I/O

# Network operations OUTSIDE lock (avoids blocking)
conn = self.config.connect()  # Can take 100ms+

# Quick state update
with self._lock:
    self._all_connections.append(conn)
```

**Design Principle**: Hold locks for minimal time, never during I/O.

## Configuration

### Setting Pool Size

```yaml
# In experiment config
parallel_queries: 8  # Sets max_workers
```

Pool size automatically matches `max_workers`:
```python
pool_size = max_workers  # No artificial cap
```

### Best Practices

1. **Match workers to queries**: Set `parallel_queries` to expected concurrency
2. **Consider Trino capacity**: Don't exceed Trino's max concurrent queries
3. **Monitor resources**: Check connection count in pool stats
4. **Enable eager creation**: For benchmarks, always use `eager_create=True`

## Monitoring

### Pool Statistics

```python
stats = pool.get_stats()
# {
#   'pool_size': 4,
#   'created_connections': 4,
#   'available_connections': 2,  # In pool queue
#   'in_use_connections': 2,      # Acquired by threads
#   'total_acquired': 15,          # Total acquisitions
#   'total_released': 13           # Total releases
# }
```

**Efficiency Metric**: `total_acquired > created_connections` proves reuse!

Example:
- Created: 4 connections
- Acquired: 20 times
- Reuse factor: 20/4 = 5x (each connection served 5 queries on average)

### Log Messages

```
[INFO] Initializing connection pool with size=4
[INFO] Pre-creating 4 connections...
[INFO] Pre-created all 4 connections
[INFO] [Parallel] Executing: query1_run1
[DEBUG] Acquired connection from pool (acquired=1)
[INFO] Pooled query completed in 0.45s, returned 100 rows
[INFO] [Parallel] Pool stats: {'created_connections': 4, 'total_acquired': 10, ...}
[INFO] Connection pool closed
```

## Comparison: Pooling vs Thread-Local

### Original Thread-Local Approach

```python
thread_local = threading.local()

def get_executor():
    if not hasattr(thread_local, 'executor'):
        thread_local.executor = QueryExecutor(...)
        thread_local.executor.connect()  # New connection
    return thread_local.executor

# Each thread creates its own executor + connection
```

**Characteristics**:
- ✅ Simple implementation
- ✅ One connection per thread (predictable)
- ❌ Creates connection on first use (lazy)
- ❌ Connections destroyed when thread ends (no reuse across runs)
- ❌ Connection count = thread count (can't limit)

### Connection Pooling Approach

```python
pool = ConnectionPool(config, pool_size=4, eager_create=True)

def execute_query_task(query):
    executor.execute_with_pool(query, pool)
    # Connection acquired from pool, released after use
```

**Characteristics**:
- ✅ All connections pre-created (eager mode)
- ✅ Connections reused across queries and runs
- ✅ Bounded connection count (pool_size limit)
- ✅ Better resource management
- ✅ Connection stats/monitoring
- ⚠️  Slightly more complex

## Performance Tips

### 1. Right-Size the Pool

```python
# Too small: Threads wait for connections
pool_size = 2, max_workers = 10  # ❌ 8 threads waiting

# Too large: Wasted resources
pool_size = 100, max_workers = 4  # ❌ 96 unused connections

# Just right: Match workers
pool_size = 10, max_workers = 10  # ✅ Perfect match
```

### 2. Use Eager Creation for Benchmarks

```python
# Benchmark setup
ConnectionPool(config, pool_size=4, eager_create=True)  # ✅

# Long-running service
ConnectionPool(config, pool_size=4, eager_create=False)  # ✅
```

### 3. Monitor Pool Stats

```python
# After execution
stats = pool.get_stats()
if stats['total_acquired'] == stats['created_connections']:
    print("⚠️  No reuse - check if pool size matches workload")
```

### 4. Handle Timeouts Gracefully

```python
pool = ConnectionPool(config, timeout=30.0)  # Don't wait forever

# If you see timeout errors:
# - Increase pool_size
# - Reduce max_workers  
# - Optimize query performance
```

## Code Flow Summary

```
Experiment Start
    ↓
Create ConnectionPool (eager_create=True)
    ↓
Pre-create all connections → Add to queue
    ↓
ThreadPoolExecutor.submit(execute_query_task) × N queries
    ↓
Each thread:
    pool.acquire() → Get connection from queue
    cursor.execute(query)
    pool.release() → Put connection back
    ↓
All queries complete
    ↓
pool.get_stats() → Log statistics
    ↓
pool.close_all() → Close all connections
    ↓
Experiment End
```

## Troubleshooting

### Slow Performance

**Symptom**: Pooled execution slower than expected

**Possible Causes**:
1. Pool size < max_workers (threads waiting)
   - Check logs: `"Waiting for connection"`
   - Fix: Increase pool_size or reduce max_workers

2. Lazy creation overhead
   - Check: `eager_create=False`
   - Fix: Set `eager_create=True`

3. Lock contention
   - Check logs: Delays between acquire/release
   - Fix: Already optimized (locks held minimally)

### Hanging/Deadlock

**Symptom**: Experiment stuck, no progress

**Possible Causes**:
1. Connection timeout
   - Check logs: Last message before hang
   - Fix: Increase timeout or check Trino availability

2. All connections in use
   - Check: `in_use_connections == pool_size`
   - Fix: Increase pool_size

3. Failed to release connection
   - Check: `total_acquired > total_released` after run
   - Fix: Ensure exception handling releases connections

### Memory Issues

**Symptom**: High memory usage

**Possible Causes**:
1. Too many connections
   - Check: `created_connections` value
   - Fix: Reduce pool_size

2. Connections not closed
   - Check: `close_all()` called in cleanup
   - Fix: Ensure cleanup() runs on experiment end
