# Deploying TriBench on Google Cloud Platform (GKE)

This guide explains how to deploy and test TriBench on Google Kubernetes Engine (GKE) with real cloud infrastructure.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [GCP Setup](#gcp-setup)
3. [Create GKE Cluster](#create-gke-cluster)
4. [Deploy TriBench](#deploy-tribench)
5. [Run Benchmarks](#run-benchmarks)
6. [Cost Optimization](#cost-optimization)
7. [Cleanup](#cleanup)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
```bash
# Google Cloud SDK (gcloud CLI)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# kubectl (usually comes with gcloud)
gcloud components install kubectl

# TriBench framework
git clone https://github.com/AdamLinYuan/tribench-framework
cd tribench-framework
conda env create -f environment.yml
conda activate tribench
pip install -e .
```

### GCP Account Requirements
- Active GCP project with billing enabled
- Sufficient quotas:
  - **CPUs**: 12+ cores (for 3 n2-standard-4 nodes)
  - **Persistent Disk**: 300GB+
  - **IP addresses**: 3+ external IPs
- Estimated cost: **$5-10/day** for testing (see [Cost Optimization](#cost-optimization))

---

## GCP Setup

### 1. Authenticate and Configure Project
```bash
# Login to GCP
gcloud auth login

# List your projects
gcloud projects list

# Set your project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
```

### 2. Check Quotas
```bash
# Check your compute quotas
gcloud compute project-info describe --project=$PROJECT_ID \
  --format="table(quotas.metric,quotas.usage,quotas.limit)"

# Important quotas to verify:
# - CPUS: Need 12+ (3 nodes × 4 vCPUs)
# - DISKS_TOTAL_GB: Need 300+ (3 nodes × 100GB)
# - IN_USE_ADDRESSES: Need 3+
```

---

## Create GKE Cluster

### Option 1: Standard Configuration (Recommended for Testing)

```bash
# Create 3-node cluster with autoscaling
gcloud container clusters create tribench-cluster \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n2-standard-4 \
  --disk-size 100 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 6 \
  --enable-autorepair \
  --enable-autoupgrade \
  --addons HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver

# This creates:
# - 3 worker nodes
# - 4 vCPUs, 16GB RAM per node (n2-standard-4)
# - 100GB disk per node
# - Auto-scaling enabled (3-6 nodes)
# - Estimated cost: ~$6/day
```

### Option 2: Larger Configuration (For Serious Benchmarking)

```bash
# Create 5-node cluster with more resources
gcloud container clusters create tribench-cluster \
  --region us-central1 \
  --num-nodes 5 \
  --machine-type n2-standard-8 \
  --disk-size 200 \
  --enable-autoscaling \
  --min-nodes 5 \
  --max-nodes 10 \
  --enable-autorepair \
  --enable-autoupgrade

# This creates:
# - 5 worker nodes
# - 8 vCPUs, 32GB RAM per node (n2-standard-8)
# - 200GB disk per node
# - Estimated cost: ~$20/day
```

### Option 3: Budget Configuration (Minimal Testing)

```bash
# Create minimal 2-node cluster
gcloud container clusters create tribench-cluster \
  --zone us-central1-a \
  --num-nodes 2 \
  --machine-type n2-standard-2 \
  --disk-size 50 \
  --no-enable-autoupgrade \
  --no-enable-autorepair

# This creates:
# - 2 worker nodes
# - 2 vCPUs, 8GB RAM per node (n2-standard-2)
# - 50GB disk per node
# - Estimated cost: ~$2.50/day
# - Note: May be too small for realistic benchmarks
```

### Get Cluster Credentials

```bash
# Download kubeconfig and set context
gcloud container clusters get-credentials tribench-cluster --region us-central1

# Verify connection
kubectl cluster-info
kubectl get nodes

# Check context name
kubectl config current-context
# Example output: gke_your-project_us-central1_tribench-cluster
```

---

## Deploy TriBench

### 1. Update Configuration

**Option A: Use GCP-specific config file**

```bash
# Use the pre-configured GCP settings
tribench sys setup all --kind --config config/hosts/gcp-gke.conf
```

**Option B: Set context in reference.conf**

Edit `config/reference.conf`:
```hocon
tribench {
  systems {
    kubernetes {
      # Replace with your actual context from: kubectl config current-context
      context = "gke_your-project_us-central1_tribench-cluster"
      namespace = "tribench"
      timeout = 600  # GKE can take longer for initial pulls
    }
  }
}
```

### 2. Setup Infrastructure

**Important Differences from Kind:**
- ❌ Don't run `tribench sys cluster create` (GKE cluster already exists)
- ✅ metrics-server is **pre-installed** on GKE (no manual installation needed)
- ✅ Storage classes are **pre-configured** (use `standard-rwo` for persistent volumes)

```bash
# Verify kubectl is pointing to GKE
kubectl config current-context

# Setup all systems on GKE
tribench sys setup all --kind

# This will:
# 1. Create 'tribench' namespace
# 2. Generate Kubernetes manifests
# 3. Create persistent volume claims (uses GCP persistent disks)
# 4. Deploy PostgreSQL, MinIO, Hive Metastore, Trino

# Start all systems
tribench sys start all --kind

# Check status
tribench sys status trino --kind

# Verify pods are running
kubectl -n tribench get pods
# Expected output:
# NAME                               READY   STATUS    RESTARTS   AGE
# postgresql-xxxxx                   1/1     Running   0          2m
# minio-xxxxx                        1/1     Running   0          2m
# hive-metastore-xxxxx               1/1     Running   0          90s
# trino-coordinator-xxxxx            1/1     Running   0          60s
# trino-worker-xxxxx                 1/1     Running   0          60s
```

### 3. Access Trino from Local Machine

**Option A: Port Forwarding (Simple)**
```bash
# Start port forwarding
tribench sys port-forward start

# Trino is now accessible at localhost:8080
# This runs in background - check with:
tribench sys port-forward status
```

**Option B: LoadBalancer Service (Production-like)**
```bash
# Expose Trino with GCP LoadBalancer
kubectl -n tribench expose deployment trino-coordinator \
  --type=LoadBalancer \
  --name=trino-lb \
  --port=8080 \
  --target-port=8080

# Wait for external IP (takes 1-2 minutes)
kubectl -n tribench get service trino-lb -w

# Get the external IP
export TRINO_EXTERNAL_IP=$(kubectl -n tribench get service trino-lb \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Trino accessible at http://$TRINO_EXTERNAL_IP:8080"

# Update experiments to use external IP
# Edit experiments/*.yaml:
# connection:
#   host: "$TRINO_EXTERNAL_IP"
```

### 4. Generate and Load Data

```bash
# Generate TPC-H data
tribench data generate tpch-sf1 --format parquet

# Load into Iceberg tables
tribench data load-iceberg tpch-sf1

# Validate
tribench data validate-iceberg --scale-factor 1
```

---

## Run Benchmarks

### Update Experiment Configuration for GKE

Edit `experiments/tpch-k8s-monitored.yaml`:
```yaml
# Kubernetes pod monitoring (already configured for GKE)
monitoring:
  enabled: true
  interval_seconds: 5.0
  kubernetes:
    enabled: true
    context: "gke_your-project_us-central1_tribench-cluster"  # Your actual context
    namespace: "tribench"
    label_selector: "app=trino"
    pod_name_pattern: "trino-.*"
```

### Run Experiments

```bash
# Run single experiment
tribench exp run experiments/tpch-k8s-monitored.yaml

# Run full suite
tribench suite run experiments/suites/tpch-suite.yaml

# View results
tribench res list
tribench res show 1
tribench res monitoring 1 --summary

# Export results
tribench res export 1 --format csv
```

### Verify Kubernetes Monitoring

```bash
# Check if metrics-server is available (pre-installed on GKE)
kubectl top nodes
kubectl -n tribench top pods

# Should see output like:
# NAME                           CPU(cores)   MEMORY(bytes)
# trino-coordinator-xxxxx        55m          1501Mi
# trino-worker-xxxxx             41m          2177Mi
```

---

## Cost Optimization

### Monitor Costs
```bash
# Check current costs
gcloud billing accounts list
gcloud billing projects describe $PROJECT_ID

# View cost breakdown
# Go to: https://console.cloud.google.com/billing
```

### Cost-Saving Tips

**1. Use Preemptible/Spot VMs** (70% cheaper)
```bash
gcloud container clusters create tribench-cluster \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n2-standard-4 \
  --spot  # or --preemptible for older API
```
⚠️ **Warning**: Spot VMs can be terminated anytime. Good for testing, not production benchmarks.

**2. Stop Cluster When Not in Use**
```bash
# Resize to 0 nodes (stops all VMs but keeps cluster)
gcloud container clusters resize tribench-cluster \
  --num-nodes 0 \
  --region us-central1

# Resume (scale back to 3 nodes)
gcloud container clusters resize tribench-cluster \
  --num-nodes 3 \
  --region us-central1
```

**3. Use Zonal Cluster** (Cheaper than Regional)
```bash
# Single-zone cluster (1/3 the control plane cost)
gcloud container clusters create tribench-cluster \
  --zone us-central1-a \  # Single zone, not --region
  --num-nodes 3
```

**4. Delete Cluster When Done**
```bash
# Always delete when finished testing
gcloud container clusters delete tribench-cluster --region us-central1
```

### Estimated Costs (us-central1)

| Configuration | Daily Cost | Monthly Cost |
|--------------|-----------|--------------|
| Budget (2 × n2-standard-2) | $2.50 | $75 |
| Standard (3 × n2-standard-4) | $6.00 | $180 |
| Large (5 × n2-standard-8) | $20.00 | $600 |
| Spot VMs (70% discount) | 30% of above | 30% of above |

*Costs include VMs + storage + networking. Actual costs may vary.*

---

## Cleanup

### Stop Systems
```bash
# Stop TriBench systems
tribench sys stop all --kind

# Stop port forwarding
tribench sys port-forward stop
```

### Delete GKE Cluster
```bash
# Delete the entire cluster
gcloud container clusters delete tribench-cluster --region us-central1

# Verify deletion
gcloud container clusters list
```

### Clean Local State
```bash
# Remove kubectl context
kubectl config delete-context gke_your-project_us-central1_tribench-cluster

# Remove generated manifests
rm -rf systems/kubernetes/*.yaml
```

---

## Troubleshooting

### Pods Stuck in Pending
```bash
# Check events
kubectl -n tribench get events --sort-by='.lastTimestamp'

# Common causes:
# 1. Insufficient resources - scale up cluster
gcloud container clusters resize tribench-cluster --num-nodes 5 --region us-central1

# 2. PVC not bound - check storage
kubectl -n tribench get pvc
kubectl -n tribench describe pvc <pvc-name>
```

### Trino Connection Timeout
```bash
# Check if Trino pod is ready
kubectl -n tribench get pods -l app=trino

# Check Trino logs
kubectl -n tribench logs -f deployment/trino-coordinator

# Verify port forwarding
tribench sys port-forward status
lsof -i :8080  # Check if port is in use
```

### Metrics-Server Not Working
```bash
# Check if metrics-server is installed (should be by default on GKE)
kubectl -n kube-system get deployment metrics-server

# Test metrics
kubectl top nodes
kubectl -n tribench top pods

# If not working, install manually:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Permission Errors
```bash
# Grant yourself cluster-admin
kubectl create clusterrolebinding cluster-admin-binding \
  --clusterrole=cluster-admin \
  --user=$(gcloud config get-value core/account)
```

### High Costs
```bash
# Check what's running
gcloud compute instances list
kubectl get all -A

# Resize or delete cluster
gcloud container clusters resize tribench-cluster --num-nodes 0 --region us-central1
# OR
gcloud container clusters delete tribench-cluster --region us-central1
```

---

## Key Differences: Kind vs GKE

| Feature | Kind (Local) | GKE (Cloud) |
|---------|-------------|-------------|
| **Cluster Creation** | `tribench sys cluster create` | `gcloud container clusters create` |
| **metrics-server** | Manual install needed | Pre-installed ✅ |
| **Storage** | Local disk | GCP Persistent Disks (standard-rwo) |
| **Networking** | Port forwarding required | LoadBalancer available |
| **Cost** | Free | $2-20/day |
| **Performance** | Limited by laptop | Real cloud performance |
| **Scalability** | Limited (2-3 workers) | Unlimited (autoscaling) |
| **Access** | localhost only | External IP / VPN |

---

## Next Steps

After successful GKE deployment:

1. **University Cluster**: Similar steps work for any Kubernetes cluster
   - Skip GKE-specific commands
   - Use your university's kubectl context
   - Check with cluster admin about storage classes and quotas

2. **Other Cloud Providers**:
   - **AWS EKS**: Similar process with `eksctl`
   - **Azure AKS**: Similar process with `az aks`
   - **On-Premise**: Use kubeadm or enterprise Kubernetes

3. **Production Deployment**:
   - Add Helm charts for easier deployment
   - Configure ingress controllers
   - Setup CI/CD pipelines
   - Enable monitoring (Prometheus/Grafana)

---

## Summary

**To test TriBench on GCP, you need:**

✅ GCP account with billing (~$5-10/day for testing)  
✅ `gcloud` CLI and `kubectl` installed  
✅ Create GKE cluster: `gcloud container clusters create tribench-cluster ...`  
✅ Get credentials: `gcloud container clusters get-credentials ...`  
✅ Update context in `config/reference.conf` or use `config/hosts/gcp-gke.conf`  
✅ Deploy: `tribench sys setup all --kind && tribench sys start all --kind`  
✅ Run benchmarks: `tribench exp run experiments/tpch-k8s-monitored.yaml`  
✅ Cleanup: `gcloud container clusters delete tribench-cluster`

**The framework is already 95% cloud-ready!** No major code changes needed. 🎉
