## Phase 4: Kubernetes Deployment (Week 28-29) ✅

### Section 4.1 & 4.2: Kubernetes Infrastructure & Deployment ✅
**Completed**: Full Kubernetes support using `kind` (Kubernetes in Docker) and native manifests (replacing Helm charts), integrated into the existing CLI.

#### Core Components Implemented

1. **KubernetesSystem Class** (`lib/tribench/systems/kubernetes_system.py`)
   - Complete implementation of System abstract base class for K8s
   - Wraps `kubectl` commands for cluster management
   - Manages Trino, MinIO, PostgreSQL, and Hive Metastore deployments via generated manifests
   - Handles port forwarding for local access to cluster services
   - **Dissertation Value**: Demonstrates adaptability of the framework to distributed environments

2. **Native Manifest Generation**
   - Dynamic generation of Kubernetes YAML manifests (Deployment, Service, ConfigMap)
   - Integration with `reference.conf` for centralized configuration
   - Direct translation of system requirements to Kubernetes primitives
   - **Dissertation Value**: Infrastructure-as-Code approach without external dependencies (Helm)

3. **CLI Integration**
   - Added `--kind` flag to all system commands (`setup`, `start`, `stop`, `status`, `teardown`)
   - Seamless switching between Docker Compose (default) and Kubernetes
   - Unified user experience regardless of backend

#### Implementation Details

**Lifecycle Management**:
- **Setup**: 
  - Generates Kubernetes manifests from HOCON config
  - Applies manifests using `kubectl apply`
  - Loads local Docker images into Kind cluster (Postgres, Hive)
  - Waits for pod readiness
- **Start**:
  - Applies manifests (ensuring replicas=1)
  - Establishes port forwarding (Trino: 8080, MinIO: 9000/9001)
  - Manages background processes for port forwarding
- **Stop**:
  - Scales deployments to 0 replicas (pauses system)
  - Terminates port forwarding processes
  - Preserves data and configuration
- **Teardown**:
  - Deletes all Kubernetes resources (Deployments, Services, ConfigMaps)
  - Destructive operation (uninstalls system)
- **Status**:
  - Reports Pod status (Running/Pending)
  - Verifies port forwarding connectivity
  - Checks service health endpoints

**Port Forwarding & Process Management**:
- Implemented robust port forwarding management using `subprocess`
- Tracks PIDs to prevent zombie processes
- Uses `lsof` to detect and kill conflicting processes on ports 8080/9000
- Ensures clean startup even after ungraceful shutdowns

**Error Handling & Idempotency**:
- `setup` is idempotent (uses `kubectl apply`)
- `stop` handles "resource not found" gracefully
- Validates Kubernetes environment (kubectl, kind) availability

#### Files Created/Modified

- **New**: `lib/tribench/systems/kubernetes_system.py` (Core logic)
- **Generated**: `systems/kubernetes/*.yaml` (Manifests)
- **Modified**: `lib/tribench/cli/system_commands.py` (Added `--kind` flag and config passing)
- **Modified**: `lib/tribench/systems/__init__.py` (Factory logic for system creation)

#### Technical Challenges Solved

1. **Helm Complexity vs Native Manifests**: 
   - Challenge: Helm charts introduced unnecessary complexity and failure modes for our specific use case.
   - Solution: Refactored to generate native Kubernetes manifests directly from Python system definitions, giving full control over the deployment.

2. **Image Availability in Kind**:
   - Challenge: Kind clusters cannot access local Docker images by default, and pulling from Hub failed for some images.
   - Solution: Implemented `kind load image-archive` workflow to reliably transfer locally built/pulled images (Postgres, Hive) into the cluster nodes.

3. **Zombie Port Forwarding**:
   - Challenge: `kubectl port-forward` processes often lingered after CLI exit, blocking ports for subsequent runs.
   - Solution: Added aggressive cleanup logic using `lsof -ti:{port} | xargs kill` before starting new forwards, and tracked PIDs for clean shutdown.

#### Lessons Learned

1. **Kubernetes Complexity**: Even with `kind`, K8s introduces significant complexity over Docker Compose (networking, pod scheduling).
2. **Native vs Abstraction**: Removing Helm simplified the architecture significantly. Direct manifest generation proved more robust and easier to debug than templated charts.
3. **Process Management**: Managing background processes (port-forwarding) from a CLI requires careful signal handling and cleanup to avoid resource leaks.

---

### Section 4.3: Experiment Integration (Run TPC-H on K8s) ✅
**Completed**: Full experiment execution on Kubernetes with Iceberg table format, persistent port forwarding management, and comprehensive demo experiments.

#### Core Components Implemented

1. **Persistent Port Forwarding Management**
   - PID file persistence (`log/port-forward.pid`) for cross-session survival
   - New CLI command: `tribench sys port-forward start|stop|status`
   - Auto-detection and restart of port forwarding when PID file exists
   - **Dissertation Value**: Demonstrates robust distributed system management in CLI tools

2. **Auto-Detection of K8s Deployment**
   - `auto_ensure_trino_connection()` function in `lib/tribench/cli/base.py`
   - Checks socket connectivity before each Trino-dependent command
   - Automatically restarts port forwarding if PID file exists but connection is lost
   - Fallback to `--kind` flag for explicit K8s mode

3. **Iceberg Data Loading on K8s**
   - `tribench data load-iceberg --dataset tpch-sf0_01` working with K8s backend
   - Automatic catalog/schema detection from connection settings
   - TPC-H data generation and Iceberg table creation via Trino

4. **Demo Experiments Suite**
   - Created `experiments/demo/` directory with 6 focused experiments
   - Comprehensive suite combining all experiments: `experiments/suites/tpch-demo-suite.yaml`
   - Coverage of all TPC-H query patterns (aggregation, joins, subqueries, analytics)

#### Implementation Details

**Port Forwarding Lifecycle**:
```
┌─────────────────────────────────────────────────────────────────┐
│ tribench sys port-forward start                                 │
│   1. Check for stale PID files (cleanup zombie processes)       │
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

**Demo Experiments Created**:

| Experiment | Queries | Focus | Est. Time |
|------------|---------|-------|-----------|
| `tpch-quick-smoke.yaml` | 3 inline queries | System validation | < 1 min |
| `tpch-aggregation-demo.yaml` | Q1, Q6 | GROUP BY, SUM | ~2-3 min |
| `tpch-join-demo.yaml` | Q3, Q5, Q10 | Multi-table joins | ~3-4 min |
| `tpch-subquery-demo.yaml` | Q4, Q11, Q22 | EXISTS, IN, correlated | ~3-4 min |
| `tpch-analytical-demo.yaml` | Q7, Q8, Q9 | Complex analytics | ~4-5 min |
| `tpch-top5-benchmark.yaml` | Q1, Q3, Q5, Q6, Q14 | Representative benchmark | ~5-7 min |

**Demo Suite Structure**:
```yaml
# experiments/suites/tpch-demo-suite.yaml
experiments:
  - smoke-test     # Stage 1: Validate connectivity
  - aggregation    # Stage 2: Simple patterns
  - joins          # Stage 3: Join performance
  - subqueries     # Stage 4: Complex patterns
  - analytical     # Stage 5: Business intelligence
  - top5-benchmark # Stage 6: Comprehensive benchmark
```

#### Files Created/Modified

**New Files**:
- `experiments/demo/tpch-quick-smoke.yaml` - Quick validation experiment
- `experiments/demo/tpch-aggregation-demo.yaml` - Aggregation queries (Q1, Q6)
- `experiments/demo/tpch-join-demo.yaml` - Join queries (Q3, Q5, Q10)
- `experiments/demo/tpch-subquery-demo.yaml` - Subquery patterns (Q4, Q11, Q22)
- `experiments/demo/tpch-analytical-demo.yaml` - Analytical queries (Q7, Q8, Q9)
- `experiments/demo/tpch-top5-benchmark.yaml` - Top 5 representative queries
- `experiments/demo/README.md` - Demo experiments documentation
- `experiments/suites/tpch-demo-suite.yaml` - Comprehensive demo suite

**Modified Files**:
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
  - Added `--kind` flag to `load`, `load-iceberg`, `validate-iceberg` commands
  - Integrated `auto_ensure_trino_connection()` for automatic port forwarding

- `lib/tribench/cli/experiment_commands.py`:
  - Added `--kind` flag to `exp run` command
  - Integrated `auto_ensure_trino_connection()` for automatic port forwarding

- `lib/tribench/cli/suite_commands.py`:
  - Added `--kind` flag to `suite run` command
  - Integrated `auto_ensure_trino_connection()` for automatic port forwarding

#### Technical Challenges Solved

1. **Cross-Session Port Forwarding Persistence**:
   - Challenge: Port forwarding dies when terminal closes, requiring manual restart
   - Solution: PID file persistence at `log/port-forward.pid` allows detecting and managing forwarding across CLI sessions

2. **Automatic K8s Detection**:
   - Challenge: Users shouldn't need to remember `--kind` for every command
   - Solution: `auto_ensure_trino_connection()` checks PID file existence to detect K8s mode and auto-restarts forwarding

3. **Stale Process Cleanup**:
   - Challenge: Zombie port-forward processes block ports after crashes
   - Solution: `_cleanup_stale_port_forward()` validates PID file contents and kills orphaned processes

4. **Connection Refused During Iceberg Load**:
   - Challenge: `tribench data load-iceberg` failed with "Connection refused" despite K8s running
   - Solution: Integrated port forwarding check at command startup, not just in system lifecycle

#### Query Pattern Coverage

The demo experiments provide comprehensive coverage of TPC-H query patterns:

```
Query Patterns Tested:
├── Aggregation (Q1, Q6)
│   ├── Heavy GROUP BY with multiple columns
│   └── Simple scan with aggregation
├── Joins (Q3, Q5, Q10)
│   ├── 3-way join (lineitem → orders → customer)
│   ├── 6-way join (most tables in schema)
│   └── 4-way join with filtering
├── Subqueries (Q4, Q11, Q22)
│   ├── EXISTS subquery
│   ├── Correlated subquery with HAVING
│   └── Complex nested subqueries
└── Analytical (Q7, Q8, Q9)
    ├── Multi-year shipping analysis
    ├── Market share with CASE expressions
    └── Profit analysis with complex joins
```

#### Usage Examples

```bash
# Start port forwarding (persists across sessions)
tribench sys port-forward start

# Check status
tribench sys port-forward status
# Output: ✓ Port forwarding is active on localhost:8080

# Load Iceberg data (auto-detects K8s, restarts forwarding if needed)
tribench data load-iceberg --dataset tpch-sf0_01

# Run quick smoke test
tribench exp run experiments/demo/tpch-quick-smoke.yaml

# Run full demo suite
tribench suite run experiments/suites/tpch-demo-suite.yaml

# Stop port forwarding when done
tribench sys port-forward stop
```

#### Lessons Learned

1. **User Experience Over Explicit Flags**: Auto-detection of K8s mode via PID file provides better UX than requiring `--kind` on every command.

2. **Stateful Background Processes**: PID file persistence is essential for managing background processes in CLI tools that span multiple invocations.

3. **Query Pattern Diversity**: TPC-H queries naturally cluster into patterns (aggregation, joins, subqueries, analytics), making them ideal for focused demo experiments.

4. **Suite Composition**: Breaking experiments into focused categories allows flexible demo composition—run all or pick specific patterns.

---

### Next Steps
- 🔄 Phase 4.4: Monitoring Integration (K8s metrics)
