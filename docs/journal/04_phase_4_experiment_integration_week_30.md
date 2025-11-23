## Phase 4 Continued: Experiment Integration (Week 30) 🔄

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

### Next Steps
- Run TPC-H SF0.01 (Tiny) on the K8s cluster to verify end-to-end execution.
- Verify result retrieval and validation.
