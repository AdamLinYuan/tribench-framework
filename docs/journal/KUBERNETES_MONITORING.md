# Kubernetes Monitoring Setup Guide

## Overview

TriBench supports monitoring Kubernetes pod resources (CPU and memory) during benchmark execution using the `KubernetesPodMonitor` class. This guide explains the requirements and setup process.

## Prerequisites

### 1. kubectl CLI

The Kubernetes monitoring requires `kubectl` to be installed and configured:

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Verify installation
kubectl version --client
```

### 2. Kubernetes metrics-server

The `kubectl top` command (used for pod metrics collection) requires **metrics-server** to be deployed in your cluster.

#### Check if metrics-server is installed:

```bash
kubectl get deployment metrics-server -n kube-system
```

If you see:
```
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
metrics-server   1/1     1            1           5d
```

Then metrics-server is already installed. ✅

If you see `Error from server (NotFound)`, you need to install it. ❌

#### Install metrics-server:

**For Kind clusters (local development):**

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For Kind, you need to patch metrics-server to allow insecure TLS
kubectl patch -n kube-system deployment metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

**For production Kubernetes clusters:**

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

**Verify metrics-server is working:**

```bash
# Wait for metrics-server to start (may take 30-60 seconds)
kubectl wait --for=condition=available --timeout=60s deployment/metrics-server -n kube-system

# Test pod metrics collection
kubectl top pods -A
```

You should see output like:
```
NAMESPACE     NAME                              CPU(cores)   MEMORY(bytes)
default       trino-coordinator-abc123          150m         2048Mi
default       trino-worker-1-def456             500m         4096Mi
```

If you see `error: Metrics API not available`, wait a bit longer and try again.

## Configuration

### MonitoringConfig

Configure Kubernetes monitoring in your experiment YAML:

```yaml
# experiments/tpch-k8s-monitored.yaml
name: "tpch-k8s-with-monitoring"
description: "TPC-H benchmark with Kubernetes pod monitoring"

system: "trino"
connection:
  host: "localhost"
  port: 8080
  user: "tribench"
  catalog: "iceberg"
  schema: "tpch_sf1"

# Monitoring configuration
monitoring:
  enabled: true
  interval_seconds: 5.0  # Collect metrics every 5 seconds
  
  # Enable Kubernetes monitoring
  kubernetes:
    enabled: true
    context: "kind-tribench"       # Your K8s context
    namespace: "default"            # Namespace where Trino pods run
    label_selector: "app=trino"     # Filter pods by label (optional)
    pod_name_pattern: "trino-.*"    # Filter pods by regex (optional)
  
  # Storage options
  store_timeseries: true
  export_csv: true
  export_json: true
  output_dir: "results/monitoring"

query_files:
  - "apps/tpch/queries/q01.sql"
  - "apps/tpch/queries/q06.sql"
```

### Programmatic Usage

You can also create a `KubernetesPodMonitor` programmatically:

```python
from tribench.monitoring import KubernetesPodMonitor, MonitoringConfig, MonitoringSession

# Create monitoring configuration
config = MonitoringConfig(
    enabled=True,
    interval_seconds=5.0,
    collect_system_resources=True,
    store_timeseries=True
)

# Create Kubernetes pod monitor
k8s_monitor = KubernetesPodMonitor(
    config=config,
    context="kind-tribench",
    namespace="default",
    label_selector="app=trino",  # Only monitor Trino pods
    pod_name_pattern=r"trino-.*"  # Only pods matching pattern
)

# Create monitoring session
session = MonitoringSession(
    config=config,
    experiment_name="tpch-q1-k8s",
    collectors=[k8s_monitor]
)

# Start monitoring
session.start()

# ... run your benchmark ...

# Stop monitoring
session.stop()

# Get collected metrics
metrics = session.get_metrics()
```

## Monitoring Targets

### Label Selectors

Filter pods by Kubernetes labels:

```python
# Monitor only Trino pods
label_selector="app=trino"

# Monitor only coordinator
label_selector="app=trino,component=coordinator"

# Monitor only workers
label_selector="app=trino,component=worker"

# Monitor all Trino components
label_selector="app=trino"
```

### Pod Name Patterns

Filter pods by regex pattern:

```python
# Only coordinators
pod_name_pattern=r".*coordinator.*"

# Only workers
pod_name_pattern=r".*worker.*"

# All Trino pods
pod_name_pattern=r"trino-.*"

# Specific worker
pod_name_pattern=r"trino-worker-1-.*"
```

## Collected Metrics

The `KubernetesPodMonitor` collects the following metrics for each pod:

### CPU Metrics
- **pod_cpu_millicores**: CPU usage in millicores (1000m = 1 core)
- **pod_cpu_cores**: CPU usage in cores

### Memory Metrics
- **pod_memory_bytes**: Memory usage in bytes
- **pod_memory_mb**: Memory usage in megabytes
- **pod_memory_gb**: Memory usage in gigabytes

### Labels

Each metric includes the following labels:
- `pod`: Pod name (e.g., "trino-coordinator-abc123")
- `namespace`: Kubernetes namespace
- `component`: Component type (coordinator, worker)
- `role`: Pod role (coordinator, worker)
- `system`: System name (trino, minio, postgres, hive-metastore)

## Storage

Metrics are stored in the configured output directory with timestamps:

```
results/monitoring/
└── tpch-q1-k8s_20251219_143022/
    ├── metrics.csv              # Time-series data (if export_csv=true)
    ├── metrics.json             # JSON format (if export_json=true)
    └── summary.json             # Aggregated statistics
```

### CSV Format Example

```csv
timestamp,metric_type,name,value,unit,pod,namespace,component,system
2025-12-19T14:30:22,system_resource,pod_cpu_millicores,150,millicores,trino-coordinator-abc123,default,coordinator,trino
2025-12-19T14:30:22,system_resource,pod_cpu_cores,0.15,cores,trino-coordinator-abc123,default,coordinator,trino
2025-12-19T14:30:22,system_resource,pod_memory_mb,2048.0,MB,trino-coordinator-abc123,default,coordinator,trino
```

## Troubleshooting

### Error: "kubectl not available"

**Solution:** Install kubectl CLI (see Prerequisites above)

### Error: "Cannot connect to cluster 'kind-tribench'"

**Solution:** Verify your Kubernetes context:

```bash
# List available contexts
kubectl config get-contexts

# Switch to correct context
kubectl config use-context kind-tribench

# Verify connection
kubectl cluster-info
```

### Error: "metrics-server not available in cluster"

**Solution:** Install metrics-server (see Prerequisites above):

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For Kind clusters, also patch for insecure TLS:
kubectl patch -n kube-system deployment metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

# Wait for it to start
kubectl wait --for=condition=available --timeout=60s deployment/metrics-server -n kube-system
```

### Error: "Metrics API not available"

**Causes:**
1. metrics-server still starting up (wait 30-60 seconds)
2. metrics-server crashed or not deployed

**Solution:**

```bash
# Check metrics-server status
kubectl get deployment metrics-server -n kube-system
kubectl logs -n kube-system deployment/metrics-server

# Restart metrics-server
kubectl rollout restart deployment/metrics-server -n kube-system
kubectl wait --for=condition=available --timeout=60s deployment/metrics-server -n kube-system

# Test manually
kubectl top pods
```

### Metrics show "0m" CPU or very low values

**Cause:** Pod just started, metrics not yet available

**Solution:** Wait 10-15 seconds for kubelet to collect initial metrics

### No pods found

**Causes:**
1. Wrong namespace
2. Label selector doesn't match any pods
3. Pattern filter too restrictive

**Solution:**

```bash
# List all pods in namespace
kubectl get pods -n default

# List pods with labels
kubectl get pods -n default --show-labels

# Check if Trino pods are labeled correctly
kubectl get pods -n default -l app=trino
```

## Performance Considerations

### Collection Interval

- **Recommended:** 5-10 seconds for production benchmarks
- **High-frequency:** 1-2 seconds for short tests (increases overhead)
- **Low-frequency:** 15-30 seconds for long-running tests

```python
config = MonitoringConfig(
    interval_seconds=5.0  # Adjust based on your needs
)
```

### Metrics-server Load

The `kubectl top` command queries the metrics-server API. Excessive polling can:
- Increase cluster API server load
- Slow down metric collection

**Best practices:**
- Don't poll faster than 1 second
- Use label selectors to reduce number of pods queried
- Monitor only necessary pods

## Integration with Experiment Results

Kubernetes pod metrics are automatically integrated with experiment results:

```python
from tribench.storage import ResultStorage

storage = ResultStorage()
experiment = storage.get_experiment_by_name("tpch-q1-k8s")

# Get metrics for specific run
metrics = storage.get_run_metrics(run_id=1, metric_type="system_resource")

# Filter to pod metrics only
pod_metrics = [m for m in metrics if m['name'].startswith('pod_')]

# Analyze CPU usage over time
import pandas as pd
df = pd.DataFrame(pod_metrics)
cpu_df = df[df['name'] == 'pod_cpu_cores']
print(cpu_df.groupby('pod')['value'].describe())
```

## Example: Full Monitoring Setup

Complete example for running TPC-H with Kubernetes monitoring:

```bash
# 1. Ensure metrics-server is installed
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For Kind:
kubectl patch -n kube-system deployment metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

# 2. Wait for metrics-server
kubectl wait --for=condition=available --timeout=60s deployment/metrics-server -n kube-system

# 3. Verify it works
kubectl top pods -A

# 4. Setup Trino on Kubernetes
tribench sys setup all --kind
tribench sys start all --kind

# 5. Load data
tribench data load-iceberg tpch-sf1 --kind

# 6. Run experiment with monitoring
tribench exp run experiments/tpch-k8s-monitored.yaml

# 7. View results
tribench res show 1

# 8. Export metrics
tribench res export 1 --format csv --output tpch-k8s-metrics.csv
```

## Next Steps

- Review collected metrics in `results/monitoring/`
- Use CSV exports for custom analysis with pandas, R, or Excel
- Integrate with visualization tools (Grafana, Kibana)
- Compare pod resource usage across different query patterns
- Identify resource bottlenecks in Trino deployment
