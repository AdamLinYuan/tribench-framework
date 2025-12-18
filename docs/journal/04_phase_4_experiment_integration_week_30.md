## Phase 4 Continued: Experiment Integration (Week 30) ✅

### Section 4.3: Experiment Engine Updates ✅
**Completed**: Updated `TrinoExperiment` and CLI to support dynamic connection parameters for Kubernetes.

#### Key Changes
1. **Deep Merge for CLI Overrides**:
   - Modified `ExperimentConfig.from_yaml` to support deep merging of CLI overrides.
   - This allows overriding specific nested parameters (like `connection.host`) without wiping out the entire section.

2. **CLI Connection Flags**:
   - Added `--host` and `--port` flags to `tribench exp run`.
   - These flags map directly to `connection.host` and `connection.port` in the experiment config.
   - Enables seamless switching between local Docker (localhost:8080) and Kubernetes port-forwarding (localhost:8080 or custom).

#### Verification
- Created unit tests to verify deep merge logic for configuration overrides.
- Confirmed that `QueryExecutor` uses the configured connection parameters, ensuring compatibility with `KubernetesSystem`'s port forwarding.

---

### Section 4.3.1: Persistent Port Forwarding Management ✅
**Completed**: Implemented robust, cross-session port forwarding that survives terminal closures.

#### Core Components

1. **PID File Persistence** (`log/port-forward.pid`):
   - Port forwarding PID stored to disk for cross-session survival
   - Enables detection of K8s mode without explicit flags
   - Cleaned up on explicit stop or detected process death

2. **New CLI Command**: `tribench sys port-forward`
   ```bash
   tribench sys port-forward start   # Start and persist port forwarding
   tribench sys port-forward stop    # Stop and cleanup PID file
   tribench sys port-forward status  # Check current status
   ```

3. **Auto-Detection Function** (`auto_ensure_trino_connection()`):
   - Called automatically by Trino-dependent commands
   - Checks socket connectivity to localhost:8080
   - If PID file exists but connection failed → auto-restart forwarding
   - Eliminates need for `--kind` flag in most cases

#### Implementation Details

**Port Forwarding Lifecycle**:
```
┌─────────────────────────────────────────────────────────────────┐
│ tribench sys port-forward start                                 │
│   1. Clean up stale PID files (kill zombie processes)           │
│   2. Kill any existing process on port 8080                     │
│   3. Start kubectl port-forward as background process           │
│   4. Store PID in log/port-forward.pid                          │
│   5. Verify connectivity to localhost:8080                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ auto_ensure_trino_connection() - Called by exp/suite commands   │
│   1. Check if Trino accessible on localhost:8080                │
│   2. If yes → return True (no action needed)                    │
│   3. If no → check for log/port-forward.pid                     │
│   4. If PID file exists → restart port forwarding               │
│   5. If no PID file → let command fail naturally                │
└─────────────────────────────────────────────────────────────────┘
```

#### Files Modified

- `lib/tribench/systems/kubernetes_system.py`:
  - Added `is_port_forwarding_active()` - Check if forwarding is running
  - Added `ensure_port_forwarding()` - Restart if needed
  - Added `_cleanup_stale_port_forward()` - Remove zombie processes
  - Updated `start_port_forwarding()` - PID persistence to file
  - Updated `stop_port_forwarding()` - Clean PID file on stop

- `lib/tribench/cli/base.py`:
  - Added `kind_option` decorator for `--kind` flag
  - Added `is_k8s_deployment_active()` - Detect K8s mode
  - Added `ensure_k8s_port_forwarding()` - Setup forwarding with feedback
  - Added `auto_ensure_trino_connection()` - Smart auto-detection

- `lib/tribench/cli/system_commands.py`:
  - Added `port-forward` command group with `start`, `stop`, `status` actions

- `lib/tribench/cli/data_commands.py`:
  - Added `--kind` flag to `load`, `load-iceberg`, `validate-iceberg`
  - Integrated `auto_ensure_trino_connection()` for auto port forwarding

- `lib/tribench/cli/experiment_commands.py`:
  - Added `--kind` flag to `exp run`
  - Integrated `auto_ensure_trino_connection()` for auto port forwarding

- `lib/tribench/cli/suite_commands.py`:
  - Added `--kind` flag to `suite run`
  - Integrated `auto_ensure_trino_connection()` for auto port forwarding

---

### Section 4.3.2: Demo Experiments & Suite ✅
**Completed**: Created comprehensive demo experiments covering all TPC-H query patterns.

#### Demo Experiments Created

| Experiment | Queries | Focus | Est. Time |
|------------|---------|-------|-----------|
| `tpch-quick-smoke.yaml` | 3 inline queries | System validation | < 1 min |
| `tpch-aggregation-demo.yaml` | Q1, Q6 | GROUP BY, SUM | ~2-3 min |
| `tpch-join-demo.yaml` | Q3, Q5, Q10 | Multi-table joins | ~3-4 min |
| `tpch-subquery-demo.yaml` | Q4, Q11, Q22 | EXISTS, IN, correlated | ~3-4 min |
| `tpch-analytical-demo.yaml` | Q7, Q8, Q9 | Complex analytics | ~4-5 min |
| `tpch-top5-benchmark.yaml` | Q1, Q3, Q5, Q6, Q14 | Representative benchmark | ~5-7 min |

---

### Section 4.3.3: MinIO Bucket Auto-Creation ✅
**Completed**: Fixed Iceberg data loading by ensuring MinIO bucket exists on deployment.

#### Problem
After K8s cluster recreation, Iceberg data loading failed with:
```
Failed to create external path s3a://warehouse/tpch.db for database tpch
Schema tpch not found
```

**Root Cause**: Hive Metastore couldn't create the schema because the MinIO `warehouse` bucket didn't exist. The bucket was created in a previous deployment but lost when pods were recreated.

#### Solution
Added automatic bucket creation during MinIO deployment:

```python
# In KubernetesSystem.start()
if component in ["all", "minio"]:
    # ... deploy MinIO ...
    self._kubectl(["rollout", "status", "deployment/minio"])
    
    # Create warehouse bucket for Iceberg/Hive
    self._ensure_minio_bucket("warehouse")
```

**New Method**: `_ensure_minio_bucket(bucket_name: str)`
- Creates bucket directory in MinIO container (`/data/{bucket_name}`)
- Sets proper permissions (`chmod 777`)
- Verifies bucket creation
- Called automatically during `tribench sys start --kind`

#### Files Modified
- `lib/tribench/systems/kubernetes_system.py`:
  - Added `_ensure_minio_bucket()` method
  - Updated `start()` to call bucket creation after MinIO deployment

#### Verification
Successfully ran smoke test after fix:
```bash
tribench data load-iceberg tpch-tiny --catalog iceberg --schema tpch
# ✓ Dataset loaded into Iceberg format (8 tables, 86,805 total rows)

tribench exp run experiments/demo/tpch-quick-smoke.yaml
# ✓ Experiment 'tpch-quick-smoke' completed successfully
```

---

### Next Steps
- 🔄 Phase 4.4: Monitoring Integration (K8s metrics)
