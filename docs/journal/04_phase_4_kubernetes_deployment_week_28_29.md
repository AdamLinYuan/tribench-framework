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

### Next Steps
- 🔄 Phase 4.3: Experiment Integration (Run TPC-H on K8s)
- 🔄 Phase 4.4: Monitoring Integration (K8s metrics)
