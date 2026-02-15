# TriBench Deployment Guide - GPG Cluster

Guide for deploying TriBench to the University of Glasgow's GPG Kubernetes cluster for distributed benchmarking experiments.

## Prerequisites

- **SSH access** to GPG nodes (via DCS SSH gateway)
- **Kubernetes cluster** already set up on GPG nodes (see cluster admin)
- **kubectl** installed on your local machine
- **TriBench** installed locally (`pip install -e .`)

## Architecture Overview

```
Your Local Machine
    ↓ SSH Tunnel
DCS SSH Gateway (dcs-ssh1)
    ↓ 
GPG Control Plane (gpgnode-XX)
    ↓ kubectl + port-forward
Kubernetes Cluster (multiple worker nodes)
    └── TriBench Pods
        ├── Trino Coordinator
        ├── MinIO (S3-compatible storage)
        ├── PostgreSQL (Hive Metastore backend)
        └── Hive Metastore (Iceberg catalog)
```

---

## Step 1: Get Kubernetes Access

### 1.1 SSH to GPG Control Plane

```bash
# SSH via DCS gateway
ssh -J dcs-ssh1 <username>@gpgnode-XX
```

Replace `gpgnode-XX` with the control plane node (ask cluster admin).

### 1.2 Get Kubeconfig

On the GPG control plane node:

```bash
# View kubeconfig
cat ~/.kube/config
```

Copy the entire content.

### 1.3 Configure Local kubectl

On your local machine:

```bash
# Backup existing config
cp ~/.kube/config ~/.kube/config.backup

# Merge or replace with GPG config
# Option 1: Replace (if you don't have other clusters)
cat > ~/.kube/config
# Paste the config from GPG control plane
# Ctrl+D to save

# Option 2: Merge (if you have multiple clusters)
# Use KUBECONFIG environment variable:
export KUBECONFIG=~/.kube/config:~/.kube/gpg-config

# Set proper permissions
chmod 600 ~/.kube/config
```

### 1.4 Test Connection

```bash
# This will fail initially (need SSH tunnel first)
kubectl cluster-info

# Expected error: "Unable to connect to the server"
```

---

## Step 2: Create SSH Tunnel

The GPG cluster is not directly accessible from the internet. You need an SSH tunnel.

### 2.1 Create Tunnel for kubectl

Open a **dedicated terminal** and run:

```bash
# Tunnel kubectl API server port
ssh -J dcs-ssh1 -L 6443:localhost:6443 <username>@gpgnode-XX -N
```

Keep this terminal running. All kubectl commands will go through this tunnel.

### 2.2 Verify kubectl Access

In a **new terminal**:

```bash
# Check cluster info
kubectl cluster-info

# Expected output:
# Kubernetes control plane is running at https://localhost:6443
# ...

# List nodes
kubectl get nodes

# Expected output (example):
# NAME         STATUS   ROLES           AGE   VERSION
# gpgnode-04   Ready    control-plane   30d   v1.28.2
# gpgnode-05   Ready    <none>          30d   v1.28.2
# gpgnode-06   Ready    <none>          30d   v1.28.2
```

---

## Step 3: Configure TriBench for GPG Cluster

### 3.1 Create GPG-Specific Configuration

Create `config/hosts/gpg.conf`:

```hocon
tribench {
  defaults {
    # Use Kubernetes backend
    backend = "kubernetes"
  }
  
  systems {
    kubernetes {
      # Context from GPG cluster kubeconfig
      context = "kubernetes-admin@kubernetes"  # Check your actual context name
      namespace = "tribench"
      
      # Use emptyDir volumes (no persistent storage needed for benchmarks)
      use_persistent_volumes = false
      
      # Disable Kind cluster creation
      create_cluster = false
    }
    
    trino {
      coordinator {
        host = "localhost"  # Will access via port-forward
        port = 8080
      }
    }
  }
}
```

### 3.2 Update Kubernetes Context in Code

Check your actual context name:

```bash
kubectl config get-contexts

# Output will show context name, e.g.:
# CURRENT   NAME                          CLUSTER      AUTHINFO
# *         kubernetes-admin@kubernetes   kubernetes   kubernetes-admin
```

Update the `context` value in `gpg.conf` to match.

---

## Step 4: Deploy TriBench to GPG Cluster

### 4.1 Set Configuration

```bash
cd /path/to/tribench-framework

# Use GPG config
export TRIBENCH_HOST_CONFIG=gpg

# Verify backend is set to Kubernetes
tribench sys status all
# Should show: "Backend: kubernetes"
```

### 4.2 Create Namespace

```bash
kubectl create namespace tribench

# Verify
kubectl get namespaces | grep tribench
```

### 4.3 Deploy Systems

```bash
# Setup all systems (generates and applies Kubernetes manifests)
tribench sys setup all --kind

# This will:
# 1. Generate Kubernetes YAML manifests
# 2. Apply them to the GPG cluster
# 3. Create pods for Trino, MinIO, PostgreSQL, Hive Metastore
```

### 4.4 Wait for Pods to Start

```bash
# Watch pods starting
kubectl get pods -n tribench -w

# Expected output (after a few minutes):
# NAME                                READY   STATUS    RESTARTS   AGE
# tribench-trino-XXX                  1/1     Running   0          2m
# tribench-minio-XXX                  1/1     Running   0          2m
# tribench-postgresql-XXX             1/1     Running   0          2m
# tribench-hive-metastore-XXX         1/1     Running   0          1m
```

---

## Step 5: Access Trino via Port Forwarding

### 5.1 Forward Trino Port

Open a **new dedicated terminal**:

```bash
# Forward Trino port
kubectl port-forward -n tribench svc/tribench-trino 8080:8080

# Keep this terminal running
```

### 5.2 Test Connection

In a **new terminal**:

```bash
# Check Trino status
curl http://localhost:8080/v1/info

# Or use tribench
tribench sys status trino --kind

# Expected: "Status: Running"
```

---

## Step 6: Load Data and Run Experiments

### 6.1 Load TPC-H Dataset

```bash
# Generate dataset (if not already generated)
tribench data generate tpch-sf1

# Load into Iceberg tables
tribench data load tpch-sf1 --kind

# Expected output:
# Loading tpch-sf1 into iceberg.tpch...
# ✓ Loaded tables:
#   - nation: 25 rows
#   - region: 5 rows
#   - customer: 150,000 rows
#   ...
```

### 6.2 Run Experiment

```bash
# Run TPC-H benchmark
tribench exp run experiments/tpch-gcp.yaml --kind

# Or create GPG-specific experiment config
tribench exp run experiments/tpch-gpg.yaml --kind --runs 10 --warmup 2
```

### 6.3 Monitor Execution

```bash
# Watch pods (queries may spawn worker pods on Trino)
kubectl get pods -n tribench -w

# Check Trino logs
kubectl logs -n tribench -l app=trino -f

# View experiment progress in TriBench output
```

---

## Step 7: Kubernetes Pod Monitoring (Optional)

### 7.1 Check if metrics-server is Installed

```bash
kubectl get deployment metrics-server -n kube-system

# If installed, you'll see:
# NAME             READY   UP-TO-DATE   AVAILABLE   AGE
# metrics-server   1/1     1            1           30d
```

### 7.2 View Pod Metrics

```bash
# CPU and memory usage
kubectl top pods -n tribench

# Output:
# NAME                              CPU(cores)   MEMORY(bytes)
# tribench-trino-XXX                500m         4Gi
# tribench-minio-XXX                50m          512Mi
# tribench-postgresql-XXX           100m         1Gi
```

### 7.3 Enable Monitoring in Experiments

TriBench will automatically collect pod metrics if metrics-server is available:

```yaml
# In experiment YAML
monitoring:
  enabled: true
  kubernetes:
    enabled: true
    interval: 5  # seconds
```

---

## Step 8: Results and Analysis

### 8.1 View Results

```bash
# Show experiment results
tribench res show <experiment-id>

# List all results
tribench res list

# Export results
tribench res export <experiment-id> --format csv
```

### 8.2 Download Results Locally

Results are stored in `results/tribench.db` locally. If running experiments from GPG cluster directly:

```bash
# Copy results database from GPG to local
scp -J dcs-ssh1 <username>@gpgnode-XX:/path/to/tribench-framework/results/tribench.db ./results/
```

---

## Step 9: Cleanup

### 9.1 Stop Systems

```bash
# Stop all TriBench systems
tribench sys stop all --kind

# This removes pods but keeps namespace
```

### 9.2 Delete Namespace (Complete Cleanup)

```bash
# Delete entire namespace
kubectl delete namespace tribench

# This removes all pods, services, configmaps, etc.
```

### 9.3 Close SSH Tunnels

Close the terminal windows running:
- SSH tunnel for kubectl (port 6443)
- Port forwarding for Trino (port 8080)

---

## Troubleshooting

### kubectl Connection Issues

**Problem:** `Unable to connect to the server: dial tcp: lookup kubernetes on ...: no such host`

**Solution:** 
1. Ensure SSH tunnel is running (`ssh -J dcs-ssh1 -L 6443:localhost:6443 ...`)
2. Check kubeconfig server URL is `https://localhost:6443`

### Pods Not Starting

**Problem:** Pods stuck in `Pending` or `ImagePullBackOff`

**Check:**
```bash
# Describe pod to see issues
kubectl describe pod -n tribench <pod-name>

# Common issues:
# - Insufficient resources: Add more worker nodes or reduce resource requests
# - Image pull errors: Check internet access on worker nodes
```

### Port Forward Fails

**Problem:** `error: unable to forward port because pod is not running`

**Solution:**
```bash
# Check pod status
kubectl get pods -n tribench

# Wait for pod to be Running
kubectl wait --for=condition=Ready pod -l app=trino -n tribench --timeout=300s

# Then retry port forward
```

### Trino Connection Refused

**Problem:** TriBench can't connect to Trino at localhost:8080

**Check:**
1. Port forwarding is running: `kubectl port-forward -n tribench svc/tribench-trino 8080:8080`
2. Trino pod is ready: `kubectl get pods -n tribench -l app=trino`
3. Test locally: `curl http://localhost:8080/v1/info`

---

## Multi-User Access

If multiple users want to run TriBench on GPG cluster:

### Option 1: Separate Namespaces

```bash
# Each user creates their own namespace
kubectl create namespace tribench-<username>

# Update config
export TRIBENCH_NAMESPACE=tribench-<username>
```

### Option 2: Scheduled Access

Coordinate with other users to avoid resource conflicts. Use different time slots for experiments.

---

## Performance Considerations

### Node Resources

GPG nodes typically have:
- **CPU:** 24-32 cores per node
- **Memory:** 128-256 GB per node
- **Storage:** Local SSDs + shared storage

### Resource Requests

Adjust in experiment config or Kubernetes manifests:

```yaml
resources:
  requests:
    cpu: "4"
    memory: "16Gi"
  limits:
    cpu: "8"
    memory: "32Gi"
```

### Scaling

To use more nodes, Kubernetes will automatically schedule pods across available workers. Ensure:
1. Sufficient worker nodes are available
2. Trino coordinator can reach all workers
3. Network plugin (Calico) is functioning

---

## Comparison: Local vs GKE vs GPG

| Feature | Local (Kind) | GKE | GPG Cluster |
|---------|-------------|-----|-------------|
| **Cluster Type** | Kind (single-node) | Managed GKE | Self-hosted kubeadm |
| **Storage** | Local volumes | GKE default SC | EmptyDir / HostPath |
| **Access** | Direct localhost | Internet + gcloud auth | SSH tunnel |
| **Nodes** | 1 (your laptop) | 3-10+ managed | 3-6 dedicated servers |
| **Network** | Calico (local) | GKE CNI | Calico |
| **Monitoring** | Local metrics | GKE monitoring | metrics-server + Prometheus |
| **Cost** | Free | $$ (pay per hour) | Free (university) |
| **Performance** | Limited (laptop) | Cloud scalable | High (dedicated HW) |

---

## Next Steps

1. ✅ Deploy TriBench to GPG cluster
2. ✅ Run reproducibility experiments (compare with local/GKE)
3. ✅ Conduct scalability studies (1, 2, 4, 6 workers)
4. ✅ Measure Kubernetes overhead vs Docker Compose
5. ✅ Generate dissertation results and graphs

---

## Quick Reference

```bash
# SSH Tunnel (keep running)
ssh -J dcs-ssh1 -L 6443:localhost:6443 <user>@gpgnode-XX -N

# Deploy TriBench
export TRIBENCH_HOST_CONFIG=gpg
tribench sys setup all --kind
tribench sys start all --kind

# Port Forward Trino (keep running)
kubectl port-forward -n tribench svc/tribench-trino 8080:8080

# Load Data
tribench data load tpch-sf1 --kind

# Run Experiment
tribench exp run experiments/tpch-gpg.yaml --kind --runs 10

# View Results
tribench res show <exp-id>

# Cleanup
tribench sys stop all --kind
kubectl delete namespace tribench
```

---

## Contact

For GPG cluster access and issues:
- **Cluster Admin:** (check with your supervisor)
- **TriBench Issues:** See main README.md
