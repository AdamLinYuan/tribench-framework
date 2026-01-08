# Phase 4: Cloud Deployment - Google Cloud Platform (GKE)

**Date**: January 7, 2026  
**Objective**: Deploy TriBench framework to Google Kubernetes Engine (GKE) to validate cloud-agnostic architecture

---

## Initial Context

After attempting Azure AKS deployment and encountering subscription restrictions (Azure for Students does not allow AKS cluster creation), we pivoted to Google Cloud Platform which offers:
- $300 free trial credits (90 days)
- No policy restrictions on GKE for free trial accounts
- Pre-installed metrics-server on GKE clusters
- Better support for student/trial accounts

---

## Prerequisites

### Required Tools
- **Google Cloud SDK**: Command-line tools for GCP
- **kubectl**: Kubernetes command-line tool (included with gcloud)
- **Docker**: For building and pushing container images
- **Docker Buildx**: For multi-architecture builds

### GCP Account Setup
1. Create a Google Cloud account at https://cloud.google.com
2. Activate $300 free trial (90 days)
3. Verify billing account is active

---

## Step-by-Step Deployment Guide

### 1. Google Cloud SDK Installation

**On macOS**:
```bash
brew install --cask google-cloud-sdk
```

**On Linux**:
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Initialize and authenticate**:
```bash
gcloud init
```

This will:
- Open browser for authentication
- Prompt you to select or create a project
- Set default region/zone

**Recommended settings**:
- Project name: `tribench`
- Default region: `us-central1`
- Default zone: `us-central1-a`

**Result**: Successfully authenticated and created project "tribench"

### 2. Add gcloud to PATH (macOS)**:
```bash
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"
# Add to ~/.zshrc for persistence
echo 'export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"' >> ~/.zshrc
```

### 3. Billing Account Setup

**List available billing accounts**:
```bash
gcloud billing accounts list
```

**Link billing account to project**:
```bash

gcloud billing projects link tribench --billing-account=<YOUR-BILLING-ACCOUNT-ID>
```

Replace `<YOUR-BILLING-ACCOUNT-ID>` with the ID from the previous command (format: `XXXXXX-XXXXXX-XXXXXX`)

### 4. API Enablement

**Enable required GCP APIs**:
```bash
gcloud services enable container.googleapis.com \
  compute.googleapis.com \
  artifactregistry.googleapis.com
```

**APIs Enabled**:
- `container.googleapis.com` - Kubernetes Engine API
- `compute.googleapis.com` - Compute Engine API  
- `artifactregistry.googleapis.com` - Artifact Registry API

**Verify APIs are enabled**:
```bash
gcloud services list --enabled | grep -E 'container|compute|artifact'
```

### 5. Install kubectl Authentication Plugin

**Required for kubectl to authenticate with GKE**:
```bash
### 6. GKE Cluster Creation

**Create the cluster**:
```bash
gcloud container clusters create tribench-cluster \
  --zone us-central1-a \
  --num-nodes 2 \
  --machine-type n2-standard-4 \
  --disk-size 100 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 4
```

**Configuration Parameters**:
- `--zone us-central1-a`: Single zone for cost savings
- `--num-nodes 2`: Start with 2 nodes
- `--machine-type n2-standard-4`: 4 vCPUs, 16GB RAM per node
- `--disk-size 100`: 100GB persistent disk per node
- `--enable-autoscaling`: Allow cluster to scale
- `--min-nodes 2 / --max-nodes 4`: Autoscaling limits

**Cluster Specifications**:
- **Cluster Name**: tribench-cluster
- **Location**: us-central1-a (single zone)
- **Node Count**: 2 nodes (scalable to 4)
- **Machine Type**: n2-standard-4
- **Total Resources**: 8 vCPUs, 32GB RAM
- **Estimated Cost**: ~$4-5/day (~$150/month)
- **Creation Time**: ~5 minutes
- **Kubernetes Version**: 1.33.5-gke.1308000

**Result**: Cluster created successfully
### 8. Artifact Registry Setup

**Why needed**: GKE cannot access local Docker images. All images must be in a cloud registry.

**Create Artifact Registry repository**:
```bash
gcloud artifacts repositories create tribench \
  --repository-format=docker \
  --location=us-central1 \
  --description="TriBench container images"
```

**Configure Docker authentication**:
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**Verify repository created**:
```bash
gcloud artifacts repositories list
```

Your registry URL will be: `us-central1-docker.pkg.dev/tribench/tribench`

---

## Building and Pushing Container Images

### 9. Build Hive Metastore for AMD64 Architecture

**Important**: GKE nodes use AMD64 architecture. If building on Apple Silicon (ARM64), you need a multi-arch build.

**Navigate to Hive Metastore directory**:
```bash
cd systems/hive-metastore-4.0.0
```

**Build and push for AMD64**:
```bash
**Temporary Workaround Applied**:

Edit `lib/tribench/defaults.py` line 87:
```python
# Change from:
CONTEXT: Final[str] = "kind-tribench"

# To:
CONTEXT: Final[str] = "gke_tribench_us-central1-a_tribench-cluster"
```

**Also update `config/reference.conf`**:
```hocon
kubernetes {
  context = "gke_tribench_us-central1-a_tribench-cluster"  # Changed from "kind-tribench"
}
```

**Why This is Bad**:
- Not scalable (can't switch between Kind/GKE/AKS easily)
- Config files are pointless if ignored
- Goes against config-driven architecture
- Requires code changes for different environments
- **Must be reverted after fixing config system**
**Build time**: ~20 minutes (includes cross-compilation and push)

**Verify image in registry**:
```bash
gcloud artifacts docker images list us-central1-docker.pkg.dev/tribench/tribench
```

### 10. Update Kubernetes Manifests for Cloud Registry

**Edit `systems/kubernetes/hive-metastore.yaml`**:

Change:
```yaml
image: tribench-hive-metastore:4.0.0
imagePullPolicy: Never
```

To:
```yaml
---

## Deploying TriBench to GKE

### 11. Deploy TriBench Infrastructure

**After applying configuration workarounds, deploy all components**:
```bash
tribench sys setup all --kind
```

**Note**: Despite using `--kind` flag, it will deploy to GKE because of the hardcoded context change.

**What gets deployed**:
1. PostgreSQL (metadata storage)
2. MinIO (object storage)
3. Hive Metastore (Iceberg catalog)
4. Trino Coordinator (query engine)
5. Trino Workers (2 replicas)

**Deployment time**: ~2-3 minutes

### 12. Verify Deployment

**Check all pods are running**:
```bash
kubectl -n tribench get pods
```

**Expected output**:
```
NAME                                READY   STATUS    RESTARTS   AGE
hive-metastore-565988665-vhcbn      1/1     Running   0          5m
minio-7c9454f94d-9khfw              1/1     Running   0          5m
postgresql-56bcd6bf9b-q5lqn         1/1     Running   0          5m
trino-coordinator-d879bc49d-l47nf   1/1     Running   0          5m
trino-worker-695cd79698-4q56j       1/1     Running   0          5m
trino-worker-695cd79698-4ztcs       1/1     Running   0          5m
```

All pods should show `1/1 Ready` and `Running` status.

**Check services**:
```bash
kubectl -n tribench get svc
```

### 13. Set Up Port Forwarding

**Forward Trino coordinator port to localhost**:
```bash
kubectl -n tribench port-forward svc/trino 8080:8080
```

Keep this terminal open. Trino UI will be accessible at http://localhost:8080

**Test connectivity**:
```bash
curl http://localhost:8080/v1/info
```

You should see Trino server information in JSON format.

### 14. Verify metrics-server

**Check metrics-server is working**:
```bash
kubectl top nodes
```

**Expected output**:
```
NAME                                              CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
gke-tribench-cluster-default-pool-0cbc7abb-qjtp   184m         4%       5855Mi          44%
gke-tribench-cluster-default-pool-0cbc7abb-qsdk   169m         4%       4010Mi          30%
```

This confirms Kubernetes pod monitoring will work during experiments.

---

## Loading Data and Running Experiments

### 15. Generate TPC-H Dataset

**Check if dataset exists**:
```bash
tribench data generate tpch-tiny
```

If dataset already exists at `datasets/tpch-sf0_01/parquet`, it will skip generation.

### 16. Load Data to Iceberg Tables

**Load TPC-H tiny dataset into Iceberg**:
```bash
tribench data load-iceberg tpch-tiny
```

**Expected output**:
```
Loading dataset: tpch-tiny
Created schema: tpch
Loading table: nation (25 rows)
Loading table: region (5 rows)
Loading table: customer (1500 rows)
Loading table: supplier (100 rows)
Loading table: part (2000 rows)
Loading table: partsupp (8000 rows)
Loading table: orders (15000 rows)
Loading table: lineitem (60175 rows)
✓ Loaded 8 tables with 87,805 total rows
```

### 17. Update Experiment Configuration

**Edit `experiments/tpch-k8s-monitored.yaml`**:

Update these fields:
```yaml
connection:
  schema: "tpch"  # Changed from "tpch_sf1" to match tiny dataset

monitoring:
  kubernetes:
    context: "gke_tribench_us-central1-a_tribench-cluster"  # Changed from "tribench-cluster"
```

### 18. Run Benchmark Experiment

**Execute experiment with Kubernetes monitoring**:
```bash
tribench exp run experiments/tpch-k8s-monitored.yaml
```

**Expected output**:
```
Experiment: tpch-k8s-monitored
Runs: 1
## Deployment Summary

### Deployed Components (as of 2026-01-07 14:40 UTC)
Executing run 1/1
  Executing: q01_run1 ... 6.12s ✓
  Executing: q06_run1 ... 1.79s ✓

✓ Experiment completed successfully
  Duration: 9.58s
  Runs completed: 2/2
  Monitoring metrics: 640 collected
```

### 19. View Results
**Services**:
- ✅ PostgreSQL: Metadata storage (1 pod)
- ✅ MinIO: Object storage (1 pod)
- ✅ Hive Metastore: Iceberg catalog (1 pod)
- ✅ Trino Coordinator: Query engine (1 pod)
- ✅ Trino Workers: Query execution (2 pods)

**Data Loaded**:
- ✅ TPC-H tiny dataset (SF 0.01)
- ✅ 8 Iceberg tables with 87,805 total rows
- ✅ Schema: `tpch`

**Testing Completed**:
- ✅ First successful benchmark on GKE
- ✅ Q01 and Q06 queries executed
- ✅ Kubernetes pod monitoring collected 640 metrics
- ✅ All systems validated and operational

**Cluster Status**:
- ⏸️ **Scaled to zero nodes** (cost saving mode)
- 💰 Current cost: ~$0.10/day (control plane only)
- 🔄 Can scale back up in ~2 minutes when needed
tribench res monitoring 1 --summary
```

**Export results**:
```bash
tribench res export 1 --format json
```

---

## Cluster Management

### Scaling Down (Save Costs)

**Scale cluster to zero nodes when not in use**:
```bash
gcloud container clusters resize tribench-cluster \
  --num-nodes 0 \
  --zone us-central1-a \
  --quiet
```

**Cost after scaling to zero**: ~$0.10/day (control plane only)

### Scaling Back Up

**Restore cluster to 2 nodes**:
```bash
gcloud container clusters resize tribench-cluster \
  --num-nodes 2 \
  --zone us-central1-a \
  --quiet
```

**Time to scale up**: ~2 minutes  
**Pods automatically restart**: Yes

### Cost Optimization Strategies
1. ✅ **Scale to zero nodes when not in use** - Implemented ($4-5/day → $0.10/day)
2. Use preemptible/spot nodes (70% cheaper) - Consider for future deployments
3. Use smaller machine types for testing - n2-standard-2 sufficient for small datasets
4. Delete cluster when completely finished - Backup results firste tribench-cluster \
  --zone us-central1-a \
  --quiet
```

**Warning**: This permanently deletes the cluster and all data.
### Immediate (Testing Phase) - ✅ COMPLETED
1. ✅ All systems deployed and running
2. ✅ TPC-H tiny dataset generated
3. ✅ Data loaded to Iceberg tables (87,805 rows)
4. ✅ Benchmark experiment executed successfully
5. ✅ Kubernetes monitoring validated (640 metrics collected)
6. ✅ Cluster scaled to zero to save costsNeverPull"

**Cause**: GKE trying to pull local Docker image  
**Solution**: Use cloud registry image (see step 9-10)

### Issue: Platform Mismatch Error

**Error**: `exec format error` or platform warnings  
**Cause**: ARM64 image on AMD64 nodes  
**Solution**: Build with `--platform linux/amd64` (see step 9)

### Issue: kubectl Can't Authenticate

**Error**: `gke-gcloud-auth-plugin not found`  
**Solution**: Install plugin (see step 5)

### Issue: API Not Enabled

**Error**: `API not enabled` when creating cluster  
**Solution**: Enable required APIs (see step 4)

### Issue: Billing Account Required

**Error**: `Billing account required`  
**Solution**: Link billing account to project (see step 3)

### Issue: Port Forwarding Disconnects

**Solution**: Run port-forward in background or use `tmux`/`screen`:
```bash
nohup kubectl -n tribench port-forward svc/trino 8080:8080 &
```

---

## Final Deployment
- Config file (`config/hosts/gcp-gke.conf`) was completely ignored
- System always tried to connect to "kind-tribench" context
- Had to manually change hardcoded value to GKE context

**Temporary Workaround Applied**:
```python
CONTEXT: Final[str] = "gke_tribench_us-central1-a_tribench-cluster"
```

**Why This is Bad**:
- Not scalable (can't switch between Kind/GKE/AKS easily)
- Config files are pointless if ignored
- Goes against config-driven architecture
- Requires code changes for different environments

### Issue 2: Config Loading Not Working

**Problem**: The `--config` flag doesn't override defaults
```bash
tribench sys setup all --kind --config config/hosts/gcp-gke.conf
# Still uses hardcoded "kind-tribench" context!
```

**Expected Behavior**: Config file should override defaults  
**Actual Behavior**: Hardcoded defaults always win

**Root Cause**: Configuration hierarchy not properly implemented for Kubernetes context

---

## TriBench Deployment to GKE

### 6. Initial Deployment Attempt
```bash
tribench sys setup all --kind
```

**Issues Encountered**:
1. Used wrong context (kind-tribench instead of GKE)
2. Hive Metastore image not accessible (local Docker image)

### 7. Artifact Registry Setup

**Problem**: GKE can't pull locally-built Docker images  
**Solution**: Push images to Google Artifact Registry

```bash
# Create repository
gcloud artifacts repositories create tribench \
  --repository-format=docker \
  --location=us-central1 \
  --description="TriBench container images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# Tag and push image
docker tag tribench-hive-metastore:4.0.0 \
  us-central1-docker.pkg.dev/tribench/tribench/hive-metastore:4.0.0
docker push us-central1-docker.pkg.dev/tribench/tribench/hive-metastore:4.0.0
```

**Issue**: ARM64 vs AMD64 platform mismatch  
**Cause**: Image built on Apple Silicon Mac (ARM64), GKE nodes use AMD64

### 8. Multi-Architecture Build
```bash
cd systems/hive-metastore-4.0.0
docker buildx build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/tribench/tribench/hive-metastore:4.0.0 \
  . --push
```

**Build Time**: ~20 minutes (cross-platform compilation + push)  
**Result**: AMD64 image successfully pushed to Artifact Registry

### 9. Kubernetes Manifest Update
```yaml
# systems/kubernetes/hive-metastore.yaml
containers:
- name: metastore
  image: us-central1-docker.pkg.dev/tribench/tribench/hive-metastore:4.0.0
  imagePullPolicy: Always  # Changed from "Never"
```

### 10. Final Deployment
```bash
kubectl -n tribench delete deployment hive-metastore
kubectl -n tribench apply -f systems/kubernetes/hive-metastore.yaml
```

**Result**: All pods running successfully

---

## Final System Status

### Deployed Components (as of 2026-01-07 14:30 UTC)

```
NAME                                READY   STATUS    RESTARTS   AGE
hive-metastore-565988665-vhcbn      1/1     Running   0          5m
minio-7c9454f94d-9khfw              1/1     Running   0          48m
postgresql-56bcd6bf9b-q5lqn         1/1     Running   0          47m
trino-coordinator-d879bc49d-l47nf   1/1     Running   0          37m
trino-worker-695cd79698-4q56j       1/1     Running   0          37m
trino-worker-695cd79698-4ztcs       1/1     Running   0          37m
```

**Services**:
- ✅ PostgreSQL: Metadata storage (1 pod)
- ✅ MinIO: Object storage (1 pod)
- ✅ Hive Metastore: Iceberg catalog (1 pod)
- ✅ Trino Coordinator: Query engine (1 pod)
- ✅ Trino Workers: Query execution (2 pods)

**Port Forwarding**: Active on localhost:8080

---

## Lessons Learned

### What Worked Well
1. **GKE Simplicity**: Much easier than Azure for student accounts
2. **Artifact Registry**: Clean integration with GKE
3. **Auto-scaling**: Built-in autoscaling works smoothly
4. **Pre-installed Tools**: metrics-server already available
5. **Free Trial Credits**: $300 provides ~60-75 days of testing

### What Needs Improvement
1. **Configuration System**: Config files don't override defaults properly
2. **Context Management**: Hardcoded contexts prevent cloud-agnostic deployment
3. **Image Building**: Need automated multi-arch builds for cloud deployment
4. **Documentation**: Cloud deployment process not documented for users

### Technical Debt Identified
1. **Hardcoded defaults** in `lib/tribench/defaults.py`
2. **Config hierarchy** not working as designed
3. **Platform-specific image builds** required manual intervention
4. **No automated image push** to cloud registries

---

## Cost Analysis

### GKE Cluster Costs (Estimated)
- **Control Plane**: $0.10/hour ($73/month)
- **Nodes**: 2 × n2-standard-4 @ $0.095/hour = $0.19/hour ($137/month)
- **Storage**: ~100GB persistent disks @ $0.17/GB/month = $17/month
- **Networking**: Minimal (<$5/month for testing)

**Total**: ~$232/month or ~$7.75/day  
**With $300 Credits**: ~38-40 days of continuous operation

### Cost Optimization Opportunities
1. Use preemptible/spot nodes (70% cheaper)
2. Scale to 0 nodes when not in use
3. Use smaller machine types for testing
4. Delete cluster when finished

---

## Next Steps

### Immediate (Testing Phase)
1. ✅ All systems deployed and running
2. ⏳ Generate TPC-H data (`tribench data generate tpch-sf0_01`)
3. ⏳ Load to Iceberg tables (`tribench data load-iceberg tpch-sf0_01`)
4. ⏳ Run benchmark experiments with Kubernetes monitoring
5. ⏳ Validate monitoring metrics collection on GKE

### Configuration System Fixes (Required)
## Success Metrics Achieved

✅ **Cloud Deployment**: Successfully deployed to production GKE cluster  
✅ **All Components Running**: 6/6 pods healthy and ready  
✅ **Data Pipeline**: 87,805 rows loaded into 8 Iceberg tables  
✅ **Benchmarking**: First successful experiment on cloud (Q01: 6.12s, Q06: 1.79s)  
✅ **Monitoring**: 640 Kubernetes pod metrics collected  
✅ **Multi-Cloud Capability**: Framework works on both Kind (local) and GKE (cloud)  
✅ **Scalability**: Cluster can auto-scale from 2-4 nodes  
✅ **Cost Management**: Cluster scaled to zero when not in use  
✅ **Cost-Effective**: Within free trial budget for testing (~$0.10/day when idle)
1. **Multi-arch Docker builds** in CI/CD pipeline
2. **Automatic image push** to cloud registries
3. **Cluster creation scripts** for each cloud provider
4. **Cost monitoring integration**
5. **Deployment validation tests**

---

## Success Metrics Achieved

✅ **Cloud Deployment**: Successfully deployed to production GKE cluster  
✅ **All Components Running**: 6/6 pods healthy and ready  
✅ **Multi-Cloud Capability**: Framework works on both Kind (local) and GKE (cloud)  
✅ **Scalability**: Cluster can auto-scale from 2-4 nodes  
✅ **Cost-Effective**: Within free trial budget for testing  

---

## Outstanding Issues

### Critical
1. ❌ **Config system doesn't work** - hardcoded defaults always win
2. ❌ **Not truly cloud-agnostic** - requires code changes per environment

### High Priority
3. ⚠️ **No automated image building** for cloud deployments
4. ⚠️ **Platform-specific builds** required manual intervention

### Medium Priority
5. ⚠️ **Cost monitoring** not integrated
6. ⚠️ **Documentation gaps** for cloud deployment process

---

## Files Modified

### Configuration Changes (Temporary Workarounds)
- `lib/tribench/defaults.py`: Changed CONTEXT to GKE context (TEMPORARY)
- `config/reference.conf`: Updated context (TEMPORARY)
- `config/hosts/gcp-gke.conf`: Created but not working as intended

### Deployment Artifacts
- `systems/kubernetes/hive-metastore.yaml`: Updated image path to Artifact Registry
- `systems/hive-metastore-4.0.0/Dockerfile`: Used for multi-arch build

### Documentation Added
- `docs/GCP_DEPLOYMENT.md`: Already existed, validated accuracy
- `docs/journal/04_phase_4_cloud_deployment_gcp.md`: This file

---

## Summary

Successfully deployed TriBench framework to Google Cloud GKE, validating the cloud-agnostic architecture design. However, discovered critical configuration system issues that prevent seamless environment switching. The hardcoded defaults and non-functional config file loading need to be addressed before the framework can be considered production-ready for multi-cloud deployment.

**Status**: ✅ Deployment successful, ⚠️ Configuration system needs redesign

**Next Phase**: Fix configuration hierarchy and implement proper cloud-agnostic context management.
