# Deploying TriBench on Microsoft Azure (AKS)

This guide explains how to deploy and test TriBench on Azure Kubernetes Service (AKS).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Azure Setup](#azure-setup)
3. [Create AKS Cluster](#create-aks-cluster)
4. [Deploy TriBench](#deploy-tribench)
5. [Run Benchmarks](#run-benchmarks)
6. [Cost Optimization](#cost-optimization)
7. [Cleanup](#cleanup)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Azure Student Programs

**Azure for Students** (No Credit Card Required! 🎉)
- Visit: https://azure.microsoft.com/en-us/free/students/
- **$100 credits** (renewable annually while student)
- **No credit card required** (best for students!)
- Instant approval with university email
- Access to all Azure services including AKS

**GitHub Student Developer Pack**
- Visit: https://education.github.com/pack
- Includes **$100 Azure credits**
- Approval: 1-2 days with .edu email

**Azure Free Tier**
- Visit: https://azure.microsoft.com/en-us/free/
- **$200 credits** for 30 days
- **12 months free** of popular services
- Requires credit card verification

### Required Tools
```bash
# Azure CLI
brew install azure-cli

# kubectl (if not already installed)
brew install kubectl

# TriBench framework
cd tribench-framework
conda activate tribench
```

---

## Azure Setup

### 1. Sign Up for Azure Student Account

**Recommended: Azure for Students (No Credit Card!)**
```bash
# 1. Go to https://azure.microsoft.com/en-us/free/students/
# 2. Click "Activate now"
# 3. Sign in with university email (.edu or university domain)
# 4. Verify student status (instant or 1-2 days)
# 5. Get $100 credits immediately
# 6. No credit card required! ✅
```

**Benefits:**
- $100 credits renewable annually
- Free services: 750 hours B1S VMs, 64GB storage
- No credit card needed
- Perfect for students!

### 2. Login to Azure
```bash
# Login to Azure
az login
# Opens browser for authentication

# List subscriptions
az account list --output table

# Set active subscription
az account set --subscription "Azure for Students"

# Verify
az account show
```

### 3. Create Resource Group
```bash
# Set variables
export RESOURCE_GROUP=tribench-rg
export LOCATION=eastus
export CLUSTER_NAME=tribench-cluster

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

---

## Create AKS Cluster

### Option 1: Standard Configuration (Recommended)

```bash
# Create AKS cluster with 3 nodes
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 6 \
  --generate-ssh-keys \
  --enable-managed-identity \
  --network-plugin azure

# This creates:
# - AKS control plane (free!)
# - 3 worker nodes (Standard_D2s_v3: 2 vCPUs, 8GB RAM)
# - Auto-scaling enabled (2-6 nodes)
# - Azure CNI networking
# - Estimated cost: ~$5/day
# - Creation time: 5-10 minutes
```

### Option 2: Free Tier Configuration (Budget)

```bash
# Create minimal cluster with B2s instances (free tier eligible)
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --generate-ssh-keys \
  --enable-managed-identity

# This creates:
# - 2 worker nodes (Standard_B2s: 2 vCPUs, 4GB RAM)
# - Free tier eligible (750 hours/month B1S)
# - Estimated cost: ~$2/day or FREE with credits
```

### Option 3: Larger Configuration (Serious Benchmarking)

```bash
# Create cluster with more resources
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 5 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10 \
  --generate-ssh-keys

# This creates:
# - 5 worker nodes (Standard_D4s_v3: 4 vCPUs, 16GB RAM)
# - Estimated cost: ~$20/day
```

### Get Cluster Credentials

```bash
# Download kubeconfig
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME

# Verify connection
kubectl get nodes

# Example output:
# NAME                                STATUS   ROLES   AGE   VERSION
# aks-nodepool1-12345678-vmss000000   Ready    agent   3m    v1.28.3
# aks-nodepool1-12345678-vmss000001   Ready    agent   3m    v1.28.3
# aks-nodepool1-12345678-vmss000002   Ready    agent   3m    v1.28.3

# Check context
kubectl config current-context
# Output: tribench-cluster
```

---

## Deploy TriBench

### 1. Create Azure Configuration

Create `config/hosts/azure-aks.conf`:
```hocon
# Microsoft Azure (AKS) Configuration

tribench {
  cloud_provider = "azure"
  
  systems {
    kubernetes {
      # Update with your actual context from: kubectl config current-context
      context = "tribench-cluster"
      namespace = "tribench"
      timeout = 600
      
      # AKS uses managed-csi storage class
      storage_class = "managed-csi"  # or "default"
    }
    
    trino {
      coordinator {
        memory = "6Gi"
        cpu = "2"
      }
      workers {
        count = 3
        memory = "12Gi"
        cpu = "4"
      }
    }
    
    minio {
      # Option 1: Use MinIO on AKS
      enabled = true
      storage = "100Gi"
      storage_class = "managed-csi"
      
      # Option 2: Use Azure Blob Storage (requires additional config)
      # enabled = false
    }
    
    postgresql {
      # Option 1: PostgreSQL on AKS
      storage = "50Gi"
      storage_class = "managed-csi"
      
      # Option 2: Use Azure Database for PostgreSQL
      # enabled = false
      # external_host = "your-postgres.postgres.database.azure.com"
    }
    
    hive_metastore {
      storage = "10Gi"
      storage_class = "managed-csi"
    }
  }
  
  monitoring {
    kubernetes {
      enabled = true
      # metrics-server is pre-installed on AKS ✅
    }
  }
}
```

### 2. Verify metrics-server

AKS includes metrics-server by default:

```bash
# Check if metrics-server is running
kubectl -n kube-system get deployment metrics-server

# Test it
kubectl top nodes

# If not working, install manually:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 3. Setup Infrastructure

```bash
# Setup all systems
tribench sys setup all --kind --config config/hosts/azure-aks.conf

# Start all systems
tribench sys start all --kind --config config/hosts/azure-aks.conf

# Check status
tribench sys status trino --kind --config config/hosts/azure-aks.conf

# Verify pods
kubectl -n tribench get pods
```

### 4. Access Trino

**Option A: Port Forwarding (Simple)**
```bash
tribench sys port-forward start --config config/hosts/azure-aks.conf
# Trino accessible at localhost:8080
```

**Option B: LoadBalancer (Production)**
```bash
# Create LoadBalancer service (uses Azure Load Balancer)
kubectl -n tribench expose deployment trino-coordinator \
  --type=LoadBalancer \
  --name=trino-lb \
  --port=8080

# Wait for external IP (1-2 minutes)
kubectl -n tribench get service trino-lb -w

# Get external IP
export TRINO_IP=$(kubectl -n tribench get service trino-lb \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Trino: http://$TRINO_IP:8080"
```

### 5. Generate and Load Data

```bash
tribench data generate tpch-sf1 --format parquet
tribench data load-iceberg tpch-sf1 --config config/hosts/azure-aks.conf
tribench data validate-iceberg --scale-factor 1
```

---

## Run Benchmarks

### Update Experiment Configuration

Edit `experiments/tpch-azure-aks.yaml`:
```yaml
name: "tpch-azure-aks"
description: "TPC-H on Azure AKS"

system: "trino"

connection:
  host: "localhost"  # or LoadBalancer IP
  port: 8080
  user: "tribench"
  catalog: "iceberg"
  schema: "tpch_sf1"

runs: 3
warmup_runs: 1

monitoring:
  enabled: true
  interval_seconds: 5.0
  kubernetes:
    enabled: true
    context: "tribench-cluster"
    namespace: "tribench"
    label_selector: "app=trino"

query_files:
  - "apps/tpch/queries/q01.sql"
  - "apps/tpch/queries/q06.sql"

metadata:
  cloud_provider: "azure"
  cluster_type: "aks"
  tags: ["tpch", "azure", "aks"]
```

### Run Experiments

```bash
tribench exp run experiments/tpch-azure-aks.yaml --config config/hosts/azure-aks.conf
tribench suite run experiments/suites/tpch-suite.yaml --config config/hosts/azure-aks.conf

# View results
tribench res list
tribench res show 1 --runs
tribench res monitoring 1 --summary
```

---

## Cost Optimization

### Monitor Costs

```bash
# Check spending
az consumption usage list \
  --start-date 2026-01-01 \
  --end-date 2026-01-02

# Or use Azure Portal: https://portal.azure.com/#blade/Microsoft_Azure_CostManagement
```

### Cost-Saving Strategies

**1. Use Spot VMs** (up to 90% cheaper)
```bash
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 6 \
  --priority Spot \
  --eviction-policy Delete \
  --spot-max-price -1
```

**2. Scale Down When Not in Use**
```bash
# Scale to 0 nodes
az aks scale \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 0

# Scale back up
az aks scale \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 3
```

**3. Stop Cluster** (New feature!)
```bash
# Stop cluster (keeps config, no compute charges)
az aks stop \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME

# Start cluster
az aks start \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME
```

**4. Use Dev/Test Pricing**
```bash
# Already applied with Azure for Students subscription
# Additional dev/test pricing for certain VMs
```

### Estimated Costs (eastus)

| Configuration | Hourly | Daily | Monthly |
|--------------|--------|-------|---------|
| Free (2 × B1S) | $0* | $0* | $0* |
| Budget (3 × B2s) | $0.15 | $3.60 | $108 |
| Standard (3 × D2s_v3) | $0.30 | $7.20 | $216 |
| Large (5 × D4s_v3) | $1.00 | $24.00 | $720 |
| Spot (90% discount) | 10% of above | 10% | 10% |

*Free tier: 750 hours/month B1S for 12 months. AKS control plane: **FREE** (Azure advantage!)

**Azure Advantage**: AKS control plane is **completely free**, unlike EKS/GKE ($0.10/hour).

---

## Cleanup

### Stop Systems
```bash
tribench sys stop all --kind --config config/hosts/azure-aks.conf
tribench sys port-forward stop
```

### Delete AKS Cluster
```bash
# Delete cluster
az aks delete \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --yes \
  --no-wait

# Or delete entire resource group (removes everything)
az group delete \
  --name $RESOURCE_GROUP \
  --yes \
  --no-wait

# Verify deletion
az aks list --output table
```

### Clean Local State
```bash
# Remove kubectl context
kubectl config delete-context tribench-cluster
```

---

## Troubleshooting

### Azure CLI Not Found
```bash
# Install Azure CLI
brew install azure-cli

# Or download directly
curl -L https://aka.ms/InstallAzureCli | bash
```

### Authentication Issues
```bash
# Re-login
az login --use-device-code

# Check account
az account show

# List subscriptions
az account list --output table

# Switch subscription
az account set --subscription "Azure for Students"
```

### Cluster Creation Fails
```bash
# Check quotas
az vm list-usage --location $LOCATION --output table

# Common issues:
# 1. Insufficient vCPU quota - request increase
# 2. Resource limit - choose different region
# 3. Subscription limit - verify student subscription active
```

### Pods Pending
```bash
# Check node resources
kubectl top nodes
kubectl describe nodes

# Scale up
az aks scale \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 5
```

### LoadBalancer Not Getting IP
```bash
# Check service
kubectl -n tribench describe service trino-lb

# Check events
kubectl -n tribench get events --sort-by='.lastTimestamp'

# Common issue: Quota exceeded
# Solution: Check Azure portal for quota limits
```

### Storage Issues
```bash
# List storage classes
kubectl get storageclass

# AKS provides several options:
# - managed-csi (default, recommended)
# - managed-premium (SSD)
# - azurefile (for ReadWriteMany)

# If PVC pending, check events:
kubectl -n tribench describe pvc <pvc-name>
```

---

## Key Differences: GKE vs EKS vs AKS

| Feature | GKE | EKS | AKS |
|---------|-----|-----|-----|
| **Creation Tool** | `gcloud` | `eksctl` | `az` |
| **Creation Time** | 5-10 min | 15-20 min | 5-10 min |
| **Control Plane** | $0.10/hour | $0.10/hour | **FREE** ✅ |
| **metrics-server** | Pre-installed | Manual | Pre-installed |
| **Storage Class** | `standard-rwo` | `gp2` | `managed-csi` |
| **LoadBalancer** | GCP LB | AWS ELB | Azure LB |
| **CLI Simplicity** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Student Credits** | $300, slow | $100, fast | **$100, instant** ✅ |
| **No Credit Card** | ❌ | ❌ | **✅ (Students)** |

**Azure Advantages for Students:**
1. ✅ **No credit card required** with Azure for Students
2. ✅ **Free AKS control plane** (saves $73/month)
3. ✅ **Instant approval** with university email
4. ✅ **$100 credits renewable** annually while student

---

## Azure Student Program Comparison

| Program | Credits | Approval | Credit Card | Renewable |
|---------|---------|----------|-------------|-----------|
| **Azure for Students** | $100 | Instant | **No** ✅ | Yes (annual) |
| **Azure Free Tier** | $200 | Instant | Yes | No (30 days) |
| **GitHub Student** | $100 | 1-2 days | No | Yes |
| **Azure Dev/Test** | Discounts | Instant | Yes | Yes |

**Best Option**: **Azure for Students** - No credit card, instant access, renewable!

---

## Quick Start Checklist

- [ ] Sign up for Azure for Students (no credit card!)
- [ ] Install Azure CLI: `brew install azure-cli`
- [ ] Login: `az login`
- [ ] Create resource group: `az group create ...`
- [ ] Create AKS cluster: `az aks create ...` (5-10 minutes)
- [ ] Get credentials: `az aks get-credentials ...`
- [ ] Verify: `kubectl get nodes`
- [ ] Update `config/hosts/azure-aks.conf`
- [ ] Deploy: `tribench sys setup all --kind --config ...`
- [ ] Run benchmarks: `tribench exp run ...`
- [ ] Cleanup: `az aks delete ...` or `az aks stop ...`

---

## Why Choose Azure for Testing?

✅ **Fastest for students**: No credit card, instant approval  
✅ **Free control plane**: Save $73/month vs GKE/EKS  
✅ **Good documentation**: Excellent Microsoft docs  
✅ **Renewable credits**: $100 every year while student  
✅ **Easy CLI**: `az` command is simple and intuitive  
✅ **Stop/Start cluster**: New feature saves money  

**Perfect for dissertation work on a budget!** 🎓💰

---

## Next Steps

1. **Compare clouds**: Run same benchmarks on AWS, Azure, GCP
2. **Cost analysis**: Track spending across providers
3. **Performance comparison**: Which cloud performs best for Trino?
4. **Multi-cloud strategy**: Deploy to multiple regions

---

## Summary

**To test TriBench on Azure AKS:**

✅ Sign up for Azure for Students (instant, no credit card!)  
✅ Install tools: `brew install azure-cli kubectl`  
✅ Login: `az login`  
✅ Create cluster: `az aks create --name tribench-cluster ...` (5-10 min)  
✅ Get credentials: `az aks get-credentials ...`  
✅ Update config: `config/hosts/azure-aks.conf`  
✅ Deploy: `tribench sys setup all --kind --config ...`  
✅ Run benchmarks: `tribench exp run ...`  
✅ Save money: `az aks stop ...` when not using  
✅ Cleanup: `az aks delete ...`

**Estimated costs: $3-7/day or FREE with student credits + free control plane!** 🎉
