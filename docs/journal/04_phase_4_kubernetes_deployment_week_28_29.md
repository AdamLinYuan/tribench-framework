## Phase 4: Kubernetes Deployment (Week 28-29) ✅

### Section 4.1 & 4.2: Kubernetes Infrastructure & Deployment ✅
**Completed**: Full Kubernetes support using `kind` (Kubernetes in Docker) and Helm charts, integrated into the existing CLI.

#### Core Components Implemented

1. **KubernetesSystem Class** (`lib/tribench/systems/kubernetes_system.py`)
   - Complete implementation of System abstract base class for K8s
   - Wraps `kubectl` and `helm` commands for cluster management
   - Manages Trino and MinIO deployments via Helm charts
   - Handles port forwarding for local access to cluster services
   - **Dissertation Value**: Demonstrates adaptability of the framework to distributed environments

2. **Helm Configuration Generation**
   - Dynamic generation of `values.yaml` for Trino and MinIO
   - Integration with `reference.conf` for centralized configuration
   - Configurable resource limits (CPU, Memory) and worker counts
   - **Dissertation Value**: Infrastructure-as-Code approach for reproducible deployments

3. **CLI Integration**
   - Added `--kind` flag to all system commands (`setup`, `start`, `stop`, `status`)
   - Seamless switching between Docker Compose (default) and Kubernetes
   - Unified user experience regardless of backend

#### Implementation Details

**Lifecycle Management**:
- **Setup**: 
  - Generates Helm values from HOCON config
  - Installs/Upgrades Helm releases (`tribench-trino`, `tribench-minio`)
  - Waits for pod readiness
- **Start**:
  - Checks pod status
  - Establishes port forwarding (Trino: 8080, MinIO: 9000/9001)
  - Manages background processes for port forwarding
- **Stop**:
  - Terminates port forwarding processes
  - Uninstalls Helm releases
  - Cleans up associated Jobs and resources
  - Suppresses errors for idempotent operations
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
- `setup` is idempotent (uses `helm upgrade --install`)
- `stop` handles "release not found" gracefully
- Suppresses noise from `helm uninstall` when systems are already stopped
- Validates Kubernetes environment (kubectl, helm, kind) availability

#### Files Created/Modified

- **New**: `lib/tribench/systems/kubernetes_system.py` (Core logic)
- **New**: `config/kubernetes/trino-values.yaml` (Base template)
- **New**: `config/kubernetes/minio-values.yaml` (Base template)
- **Modified**: `lib/tribench/cli/system_commands.py` (Added `--kind` flag and config passing)
- **Modified**: `lib/tribench/systems/__init__.py` (Factory logic for system creation)

#### Technical Challenges Solved

1. **Configuration Bridge**: 
   - Challenge: Mapping flat HOCON config to nested Helm values.
   - Solution: Implemented a translation layer in `KubernetesSystem.setup` to generate correct `values.yaml` dynamically.

2. **Zombie Port Forwarding**:
   - Challenge: `kubectl port-forward` processes often lingered after CLI exit, blocking ports for subsequent runs.
   - Solution: Added aggressive cleanup logic using `lsof -ti:{port} | xargs kill` before starting new forwards, and tracked PIDs for clean shutdown.

3. **Job Cleanup**:
   - Challenge: Helm uninstall didn't remove K8s Jobs (e.g., MinIO make-bucket hooks), causing conflicts on reinstall.
   - Solution: Added explicit `kubectl delete jobs` to the stop sequence.

#### Lessons Learned

1. **Kubernetes Complexity**: Even with `kind`, K8s introduces significant complexity over Docker Compose (networking, pod scheduling, helm state).
2. **Process Management**: Managing background processes (port-forwarding) from a CLI requires careful signal handling and cleanup to avoid resource leaks.
3. **Idempotency is Key**: Users often run `setup` or `stop` multiple times; the system must handle these cases without crashing or erroring.

### Next Steps
- 🔄 Phase 4.3: Experiment Integration (Run TPC-H on K8s)
- 🔄 Phase 4.4: Monitoring Integration (K8s metrics)
