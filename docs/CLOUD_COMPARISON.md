# Cloud Provider Comparison for TriBench Testing

Quick comparison to help you choose the best cloud provider for testing TriBench on a real Kubernetes cluster.

## TL;DR - Which Should You Use?

| Situation | Recommendation | Why |
|-----------|---------------|-----|
| **Need to start NOW** | **Azure** 🥇 | No credit card, instant approval |
| **GCP taking too long** | **AWS or Azure** | Both faster approval |
| **On a budget** | **Azure** 🥇 | Free control plane saves $73/month |
| **Want free tier** | **AWS** | 750 hours/month free for 12 months |
| **Most credits** | **GCP** | $300 (but slower approval) |
| **Best for students** | **Azure** 🥇 | No credit card + renewable |
| **Easiest to use** | **Azure or GCP** | Simpler CLI commands |

---

## Quick Comparison Table

| Feature | AWS (EKS) | Azure (AKS) | GCP (GKE) |
|---------|-----------|-------------|-----------|
| **Student Credits** | $100 | **$100** ✅ | $300 |
| **Approval Time** | 1-2 days | **Instant** ✅ | 3-5 days |
| **Credit Card Required** | Yes (Free Tier) | **No** ✅ | Yes |
| **Control Plane Cost** | $0.10/hr ($73/mo) | **FREE** ✅ | $0.10/hr ($73/mo) |
| **Cluster Creation Time** | 15-20 min | **5-10 min** ✅ | 5-10 min |
| **metrics-server** | Manual install | **Pre-installed** ✅ | **Pre-installed** ✅ |
| **CLI Complexity** | Medium (`eksctl`) | **Easy** (`az`) ✅ | Easy (`gcloud`) |
| **Free Tier** | **750h/month** ✅ | 750h/month | No free tier |
| **Stop/Start Cluster** | No | **Yes** ✅ | No |
| **Storage Class** | `gp2` | `managed-csi` | `standard-rwo` |
| **Student Renewal** | No | **Yes (annual)** ✅ | No |

---

## Detailed Cost Comparison

### Daily Costs (3-node Standard Configuration)

| Cloud | Instance Type | vCPU | RAM | Cost/Day | With Credits |
|-------|--------------|------|-----|----------|--------------|
| **AWS** | 3 × t3.large | 6 | 24GB | $12 + $2.40 = **$14.40** | 7 days free |
| **Azure** | 3 × D2s_v3 | 6 | 24GB | **$7.20** (no control plane!) | 14 days free |
| **GCP** | 3 × n2-standard-2 | 6 | 24GB | $6 + $2.40 = **$8.40** | 36 days free |

*Control plane: AWS/GCP $0.10/hr × 24hr = $2.40/day, Azure = $0*

### Free Tier Options

**AWS Free Tier (12 months)**
- 750 hours/month t2.micro or t3.micro
- Enough for 2 nodes running 24/7 or 3 nodes 50% of time
- ⚠️ t2/t3.micro only has 1GB RAM (may be too small)

**Azure Free Tier (12 months)**
- 750 hours/month B1S instances
- B1S: 1 vCPU, 1GB RAM
- ⚠️ Also small, but FREE control plane saves extra $73/month

**GCP Free Tier**
- No free VM hours
- Only $300 credits for 90 days

### With Student Credits

| Cloud | Credits | Control Plane | Net Credits | Days (Standard) | Days (Budget) |
|-------|---------|---------------|-------------|-----------------|---------------|
| **AWS** | $100 | $73 (30d) | $27 | 2 days | 10 days |
| **Azure** | $100 | **$0** ✅ | **$100** | 14 days | 28 days |
| **GCP** | $300 | $73 (30d) | $227 | 27 days | 90 days |

**Azure Advantage**: Free control plane means your credits go 100% to compute/storage!

---

## Student Program Comparison

### Application Process

| Cloud | Program | Approval Time | Requirements | Credits |
|-------|---------|---------------|--------------|---------|
| **AWS** | AWS Educate | 1-2 days | University email | $100 |
| **AWS** | Free Tier | **Instant** | Credit card | 750h free |
| **Azure** | Azure for Students | **Instant** ✅ | University email | $100 |
| **Azure** | Free Tier | **Instant** | Credit card | $200 (30d) |
| **GCP** | Google Cloud | 3-5 days | Credit card + verification | $300 |
| **GitHub** | Student Pack | 1-2 days | .edu email | $50-100 each |

### What You Get

**AWS Educate**
- ✅ $100 credits
- ✅ 1-2 day approval
- ✅ No credit card with Educate Starter
- ❌ Limited service access
- 🔄 Not renewable

**Azure for Students**
- ✅ $100 credits
- ✅ **Instant approval** 🎉
- ✅ **No credit card required** 🎉
- ✅ Full service access
- ✅ **Renewable annually** 🎉
- ✅ Free control plane saves $73/month

**GCP Education**
- ✅ $300 credits
- ❌ 3-5 day approval (or longer)
- ❌ Requires credit card
- ✅ Full service access
- ❌ Not renewable

**Winner for Students: Azure** 🏆 (instant, no card, renewable)

---

## Setup Time Comparison

### First-Time Setup (Until First Experiment Run)

**AWS (EKS)**
```
1. Install tools (5 min)
2. Configure AWS CLI (5 min)
3. Create cluster with eksctl (20 min) ⚠️
4. Install metrics-server (2 min)
5. Deploy TriBench (10 min)
───────────────────────────────────
Total: ~42 minutes
```

**Azure (AKS)**
```
1. Install tools (5 min)
2. Configure Azure CLI (3 min)
3. Create cluster with az (8 min) ✅
4. metrics-server pre-installed ✅
5. Deploy TriBench (10 min)
───────────────────────────────────
Total: ~26 minutes ✅
```

**GCP (GKE)**
```
1. Install tools (5 min)
2. Configure gcloud (5 min)
3. Create cluster with gcloud (8 min)
4. metrics-server pre-installed ✅
5. Deploy TriBench (10 min)
───────────────────────────────────
Total: ~28 minutes
```

**Fastest: Azure** 🏆

---

## Which Should You Use?

### For Dissertation Testing (Your Case)

**Primary Recommendation: Azure AKS** 🥇

**Why:**
1. ✅ **Start immediately** - No waiting for GCP approval
2. ✅ **No credit card** - Azure for Students doesn't require one
3. ✅ **Free control plane** - Your $100 goes further ($100 vs AWS's $27 net)
4. ✅ **Renewable** - Get another $100 next year
5. ✅ **Fast cluster creation** - 5-10 minutes vs AWS's 20 minutes
6. ✅ **Stop/start feature** - Save money when not testing

**Estimated timeline:**
- Sign up: 5 minutes
- Approval: **Instant**
- First experiment: 30 minutes
- **Total: Start testing in 35 minutes!**

### Backup Option: AWS EKS

**Use AWS if:**
- You already have an AWS account
- Your university has AWS Academy membership
- You want the longest free tier (12 months)

**Note**: EKS takes 20 minutes to create cluster vs Azure's 5-10 minutes.

### Wait for GCP if:

- You need the longest testing period ($300 credits = ~27-36 days)
- Your research requires comparing all three major clouds
- You can wait 3-5 days for approval

---

## Side-by-Side Command Comparison

### Create Cluster

**AWS (EKS)**
```bash
eksctl create cluster \
  --name tribench-cluster \
  --region us-east-1 \
  --nodegroup-name tribench-nodes \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 6 \
  --managed
# Time: 15-20 minutes
```

**Azure (AKS)**
```bash
az aks create \
  --resource-group tribench-rg \
  --name tribench-cluster \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 6 \
  --generate-ssh-keys
# Time: 5-10 minutes ✅
```

**GCP (GKE)**
```bash
gcloud container clusters create tribench-cluster \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n2-standard-4 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 6
# Time: 5-10 minutes
```

### Get Credentials

**AWS**: `aws eks update-kubeconfig --name tribench-cluster --region us-east-1`  
**Azure**: `az aks get-credentials --resource-group tribench-rg --name tribench-cluster` ✅  
**GCP**: `gcloud container clusters get-credentials tribench-cluster --region us-central1`

### Scale Cluster

**AWS**: `eksctl scale nodegroup --cluster tribench-cluster --name tribench-nodes --nodes 5`  
**Azure**: `az aks scale --resource-group tribench-rg --name tribench-cluster --node-count 5` ✅  
**GCP**: `gcloud container clusters resize tribench-cluster --num-nodes 5 --region us-central1`

### Delete Cluster

**AWS**: `eksctl delete cluster --name tribench-cluster --region us-east-1`  
**Azure**: `az aks delete --resource-group tribench-rg --name tribench-cluster --yes` ✅  
**GCP**: `gcloud container clusters delete tribench-cluster --region us-central1`

**Simplest Commands: Azure** 🏆

---

## Recommendation by Use Case

### "I need to test NOW for my dissertation due soon"
→ **Azure AKS** (instant approval, start in 35 minutes)

### "I want the cheapest option"
→ **Azure AKS** (free control plane, stop/start feature)

### "I want to test for the longest time"
→ **GCP GKE** ($300 = ~36 days) but wait for approval
→ Or **AWS Free Tier** (750 hours/month for 12 months)

### "I want to compare all three clouds"
→ Sign up for all three:
1. **Start with Azure** (instant)
2. **Add AWS** (1-2 days)
3. **Wait for GCP** (3-5 days)

### "I need production-grade testing"
→ Any of them work equally well, but **Azure** is cheapest due to free control plane

### "I'm new to cloud and want easiest experience"
→ **Azure** or **GCP** (better documentation, simpler CLI)

---

## Action Plan: Start Testing Today!

### Immediate (Today): Azure AKS

```bash
# 1. Sign up for Azure for Students (5 min)
open https://azure.microsoft.com/en-us/free/students/

# 2. Install tools (5 min)
brew install azure-cli kubectl

# 3. Login (2 min)
az login

# 4. Create cluster (8 min)
az group create --name tribench-rg --location eastus
az aks create --resource-group tribench-rg --name tribench-cluster \
  --node-count 3 --node-vm-size Standard_D2s_v3 --generate-ssh-keys

# 5. Get credentials (1 min)
az aks get-credentials --resource-group tribench-rg --name tribench-cluster

# 6. Deploy TriBench (10 min)
tribench sys setup all --kind --config config/hosts/azure-aks.conf
tribench sys start all --kind --config config/hosts/azure-aks.conf

# 7. Run experiment!
tribench exp run experiments/tpch-k8s-monitored.yaml
```

**Total time: ~30 minutes to first results!** 🚀

### Parallel Track: Apply for Others

While testing on Azure:
- Apply for **AWS Educate** (get approval in 1-2 days)
- Check if **GCP** finally approved your credits
- Sign up for **GitHub Student Pack** (includes $100 Azure + $50-100 AWS)

---

## Cost Tracking Tips

### Set Up Billing Alerts

**AWS**
```bash
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json
```

**Azure**
```bash
az consumption budget create \
  --budget-name tribench-budget \
  --amount 50 \
  --time-period Start=2026-01-01 End=2026-12-31
```

**GCP**
```bash
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name=tribench-budget \
  --budget-amount=50USD
```

### Daily Cost Check

**AWS**: `aws ce get-cost-and-usage --time-period Start=2026-01-01,End=2026-01-02 --granularity DAILY --metrics BlendedCost`  
**Azure**: `az consumption usage list --start-date 2026-01-01 --end-date 2026-01-02`  
**GCP**: `gcloud billing accounts list` (use Cloud Console for detailed costs)

---

## Summary

**For your situation (GCP approval taking too long):**

✅ **Start with Azure AKS immediately** (no credit card, instant approval)  
✅ Cost: ~$7/day or FREE with $100 student credits (14+ days of testing)  
✅ Setup time: 30 minutes to first experiment  
✅ Framework is 100% compatible (same kubectl commands)  

**Parallel track:**
- Apply for AWS Educate (1-2 days, backup option)
- Keep waiting for GCP (best for long-term testing when approved)

**All three clouds work equally well with TriBench** - the framework is truly cloud-agnostic! 🎉

Choose based on your immediate needs:
- **Need to start NOW**: Azure 🥇
- **Want free tier**: AWS
- **Want most credits**: GCP (when approved)
