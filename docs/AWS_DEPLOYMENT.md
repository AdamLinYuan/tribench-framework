# Deploying TriBench on Amazon Web Services (EKS)

This guide explains how to deploy and test TriBench on Amazon Elastic Kubernetes Service (EKS).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [AWS Setup](#aws-setup)
3. [Create EKS Cluster](#create-eks-cluster)
4. [Deploy TriBench](#deploy-tribench)
5. [Run Benchmarks](#run-benchmarks)
6. [Cost Optimization](#cost-optimization)
7. [Cleanup](#cleanup)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### AWS Student Programs

**AWS Educate** (Fastest Approval - Usually 1-2 days)
- Visit: https://aws.amazon.com/education/awseducate/
- **$100 credits** for students (no credit card required)
- Access to many AWS services including EKS
- Can start using immediately after approval

**AWS Academy** (Through University)
- Check if your university participates
- Often provides **$100-200 credits**
- Faster approval through institution

**AWS Free Tier** (No Approval Needed!)
- Sign up: https://aws.amazon.com/free/
- **12 months free** including:
  - 750 hours/month of t2.micro or t3.micro instances
  - 30GB EBS storage
  - Limited EKS usage
- ⚠️ Requires credit card but won't charge if you stay in free tier

### Required Tools
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# eksctl (EKS cluster management tool)
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# kubectl (if not already installed)
brew install kubectl

# TriBench framework
cd tribench-framework
conda activate tribench
```

---

## AWS Setup

### 1. Create AWS Account & Get Credits

**Option A: AWS Educate (Recommended)**
```bash
# 1. Go to https://aws.amazon.com/education/awseducate/
# 2. Sign up with university email
# 3. Wait 1-2 days for approval
# 4. Get $100 credits + access to AWS services
```

**Option B: AWS Free Tier (Immediate)**
```bash
# 1. Go to https://aws.amazon.com/free/
# 2. Create account with credit card
# 3. Start using immediately (free tier limits apply)
```

### 2. Configure AWS CLI
```bash
# Create IAM user with admin access (via AWS Console)
# Go to: IAM → Users → Create user → Attach "AdministratorAccess" policy
# Download access keys

# Configure AWS CLI
aws configure
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
aws eks list-clusters
```

### 3. Set Environment Variables
```bash
export AWS_REGION=us-east-1
export CLUSTER_NAME=tribench-cluster
```

---

## Create EKS Cluster

### Option 1: Standard Configuration (Recommended)

**Using eksctl (Easiest)**
```bash
# Create cluster with 3 nodes
eksctl create cluster \
  --name tribench-cluster \
  --region us-east-1 \
  --nodegroup-name tribench-nodes \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 6 \
  --managed

# This creates:
# - EKS control plane (managed by AWS)
# - 3 worker nodes (t3.large: 2 vCPUs, 8GB RAM)
# - Auto-scaling group (2-6 nodes)
# - VPC with subnets
# - Estimated cost: ~$5/day
# - Creation time: 15-20 minutes
```

### Option 2: Free Tier Configuration (Budget)

```bash
# Create minimal cluster with t3.micro (free tier eligible)
eksctl create cluster \
  --name tribench-cluster \
  --region us-east-1 \
  --nodegroup-name tribench-nodes \
  --node-type t3.micro \
  --nodes 2 \
  --managed

# This creates:
# - 2 worker nodes (t3.micro: 2 vCPUs, 1GB RAM)
# - Free tier eligible (750 hours/month)
# - ⚠️ May be too small for realistic benchmarks
# - Good for testing framework functionality
```

### Option 3: Larger Configuration (Serious Benchmarking)

```bash
# Create cluster with more resources
eksctl create cluster \
  --name tribench-cluster \
  --region us-east-1 \
  --nodegroup-name tribench-nodes \
  --node-type t3.xlarge \
  --nodes 5 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# This creates:
# - 5 worker nodes (t3.xlarge: 4 vCPUs, 16GB RAM)
# - Estimated cost: ~$15/day
```

### Option 4: Using Configuration File

Create `eks-cluster-config.yaml`:
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: tribench-cluster
  region: us-east-1

nodeGroups:
  - name: tribench-nodes
    instanceType: t3.large
    desiredCapacity: 3
    minSize: 2
    maxSize: 6
    volumeSize: 100
    labels:
      workload: tribench
    tags:
      Project: TriBench
      Environment: Testing
```

Deploy:
```bash
eksctl create cluster -f eks-cluster-config.yaml
```

### Verify Cluster Creation

```bash
# Wait for cluster to be ready (15-20 minutes)
eksctl get cluster --name tribench-cluster --region us-east-1

# kubectl should be automatically configured
kubectl get nodes

# Example output:
# NAME                           STATUS   ROLES    AGE   VERSION
# ip-192-168-1-10.ec2.internal   Ready    <none>   5m    v1.28.3-eks-...
# ip-192-168-1-11.ec2.internal   Ready    <none>   5m    v1.28.3-eks-...
# ip-192-168-1-12.ec2.internal   Ready    <none>   5m    v1.28.3-eks-...

# Check context
kubectl config current-context
# Output: <your-iam-user>@tribench-cluster.us-east-1.eksctl.io
```

---

## Deploy TriBench

### 1. Create AWS Configuration

Create `config/hosts/aws-eks.conf`:
```hocon
# Amazon Web Services (EKS) Configuration

tribench {
  cloud_provider = "aws"
  
  systems {
    kubernetes {
      # Update with your actual context from: kubectl config current-context
      context = "your-iam-user@tribench-cluster.us-east-1.eksctl.io"
      namespace = "tribench"
      timeout = 600
      
      # EKS uses gp2/gp3 storage class by default
      storage_class = "gp2"
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
      # Option 1: Use MinIO on EKS
      enabled = true
      storage = "100Gi"
      storage_class = "gp2"
      
      # Option 2: Use S3 instead (requires additional config)
      # enabled = false
    }
    
    postgresql {
      # Option 1: PostgreSQL on EKS
      storage = "50Gi"
      storage_class = "gp2"
      
      # Option 2: Use RDS PostgreSQL
      # enabled = false
      # external_host = "your-rds-instance.region.rds.amazonaws.com"
    }
    
    hive_metastore {
      storage = "10Gi"
      storage_class = "gp2"
    }
  }
  
  monitoring {
    kubernetes {
      enabled = true
      # metrics-server needs to be installed on EKS
    }
  }
}
```

### 2. Install metrics-server

EKS doesn't include metrics-server by default, so install it:

```bash
# Install metrics-server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Wait for it to be ready
kubectl -n kube-system wait --for=condition=ready pod -l k8s-app=metrics-server --timeout=60s

# Test it
kubectl top nodes
```

### 3. Setup Infrastructure

```bash
# Get your actual kubectl context
export EKS_CONTEXT=$(kubectl config current-context)
echo "Your EKS context: $EKS_CONTEXT"

# Update config/hosts/aws-eks.conf with the actual context

# Setup all systems
tribench sys setup all --kind --config config/hosts/aws-eks.conf

# Start all systems
tribench sys start all --kind --config config/hosts/aws-eks.conf

# Check status
tribench sys status trino --kind --config config/hosts/aws-eks.conf

# Verify pods
kubectl -n tribench get pods
```

### 4. Access Trino

**Option A: Port Forwarding (Simple)**
```bash
tribench sys port-forward start --config config/hosts/aws-eks.conf
# Trino accessible at localhost:8080
```

**Option B: LoadBalancer (Production)**
```bash
# Create LoadBalancer service (uses AWS ELB)
kubectl -n tribench expose deployment trino-coordinator \
  --type=LoadBalancer \
  --name=trino-lb \
  --port=8080

# Wait for ELB to provision (2-3 minutes)
kubectl -n tribench get service trino-lb -w

# Get external hostname
export TRINO_HOST=$(kubectl -n tribench get service trino-lb \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Trino: http://$TRINO_HOST:8080"
```

### 5. Generate and Load Data

```bash
tribench data generate tpch-sf1 --format parquet
tribench data load-iceberg tpch-sf1 --config config/hosts/aws-eks.conf
tribench data validate-iceberg --scale-factor 1
```

---

## Run Benchmarks

### Update Experiment Configuration

Edit `experiments/tpch-aws-eks.yaml`:
```yaml
name: "tpch-aws-eks"
description: "TPC-H on AWS EKS"

system: "trino"

connection:
  host: "localhost"  # or LoadBalancer hostname
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
    context: "your-iam-user@tribench-cluster.us-east-1.eksctl.io"
    namespace: "tribench"
    label_selector: "app=trino"

query_files:
  - "apps/tpch/queries/q01.sql"
  - "apps/tpch/queries/q06.sql"

metadata:
  cloud_provider: "aws"
  cluster_type: "eks"
  tags: ["tpch", "aws", "eks"]
```

### Run Experiments

```bash
tribench exp run experiments/tpch-aws-eks.yaml --config config/hosts/aws-eks.conf
tribench suite run experiments/suites/tpch-suite.yaml --config config/hosts/aws-eks.conf

# View results
tribench res list
tribench res show 1 --runs
tribench res monitoring 1 --summary
```

---

## Cost Optimization

### Monitor Costs

```bash
# Check current costs
aws ce get-cost-and-usage \
  --time-period Start=2026-01-01,End=2026-01-02 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Or use AWS Console: https://console.aws.amazon.com/cost-management/
```

### Cost-Saving Strategies

**1. Use Spot Instances** (60-90% cheaper)
```bash
eksctl create cluster \
  --name tribench-cluster \
  --region us-east-1 \
  --nodegroup-name tribench-spot \
  --node-type t3.large \
  --nodes 3 \
  --spot
```

**2. Scale Down When Not in Use**
```bash
# Scale nodegroup to 0
eksctl scale nodegroup \
  --cluster tribench-cluster \
  --name tribench-nodes \
  --nodes 0 \
  --nodes-min 0

# Scale back up
eksctl scale nodegroup \
  --cluster tribench-cluster \
  --name tribench-nodes \
  --nodes 3
```

**3. Use Free Tier Instances**
- t2.micro: 750 hours/month free for 12 months
- t3.micro: Also eligible for free tier
- ⚠️ May be too small for realistic benchmarks

**4. Delete Cluster When Done**
```bash
eksctl delete cluster --name tribench-cluster --region us-east-1
```

### Estimated Costs (us-east-1)

| Configuration | Hourly | Daily | Monthly |
|--------------|--------|-------|---------|
| Free Tier (2 × t3.micro) | $0* | $0* | $0* |
| Budget (3 × t3.small) | $0.30 | $7.20 | $216 |
| Standard (3 × t3.large) | $0.50 | $12.00 | $360 |
| Large (5 × t3.xlarge) | $1.66 | $40.00 | $1,200 |
| Spot (70% discount) | 30% of above | 30% | 30% |

*Free tier: First 750 hours/month for 12 months. EKS control plane: $0.10/hour ($73/month).

---

## Cleanup

### Stop Systems
```bash
tribench sys stop all --kind --config config/hosts/aws-eks.conf
tribench sys port-forward stop
```

### Delete EKS Cluster
```bash
# Delete cluster and all resources
eksctl delete cluster --name tribench-cluster --region us-east-1

# This deletes:
# - EKS cluster
# - EC2 instances (worker nodes)
# - VPC and networking
# - LoadBalancers
# - EBS volumes

# Verify deletion
eksctl get cluster --name tribench-cluster --region us-east-1
aws eks list-clusters --region us-east-1
```

### Clean Local State
```bash
# Remove kubectl context
kubectl config delete-context your-iam-user@tribench-cluster.us-east-1.eksctl.io
```

---

## Troubleshooting

### eksctl Command Not Found
```bash
# Install eksctl
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Or download directly
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

### Cluster Creation Fails
```bash
# Check CloudFormation stacks
aws cloudformation list-stacks --region us-east-1

# View specific stack events
aws cloudformation describe-stack-events \
  --stack-name eksctl-tribench-cluster-cluster

# Common issues:
# 1. Insufficient quotas - request limit increase
# 2. VPC limits - delete unused VPCs
# 3. IAM permissions - ensure AdministratorAccess
```

### Pods Pending (Insufficient Resources)
```bash
# Check node resources
kubectl top nodes
kubectl describe nodes

# Scale up nodegroup
eksctl scale nodegroup \
  --cluster tribench-cluster \
  --name tribench-nodes \
  --nodes 5
```

### LoadBalancer Not Getting External IP
```bash
# Check service
kubectl -n tribench describe service trino-lb

# Check events
kubectl -n tribench get events --sort-by='.lastTimestamp'

# Common issue: Security group rules
# Solution: Manually open port 8080 in EC2 security groups
```

### metrics-server Not Working
```bash
# Check if installed
kubectl -n kube-system get deployment metrics-server

# Install if missing
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Check logs
kubectl -n kube-system logs deployment/metrics-server
```

---

## Key Differences: GKE vs EKS

| Feature | GKE | EKS |
|---------|-----|-----|
| **Cluster Tool** | `gcloud` | `eksctl` |
| **Creation Time** | 5-10 min | 15-20 min |
| **Control Plane Cost** | $0.10/hour | $0.10/hour |
| **metrics-server** | Pre-installed | Manual install |
| **LoadBalancer** | GCP LB | AWS ELB/ALB |
| **Storage** | GCP Persistent Disk | AWS EBS (gp2/gp3) |
| **Free Tier** | $300 credits | 750 hours t2/t3.micro |
| **Student Credits** | Slower approval | Faster (AWS Educate) |

---

## AWS Student Program Comparison

| Program | Credits | Approval Time | Requirements |
|---------|---------|---------------|--------------|
| **AWS Educate** | $100 | 1-2 days | University email |
| **AWS Academy** | $100-200 | Immediate | University member |
| **Free Tier** | 750h free | Immediate | Credit card |
| **GitHub Student** | $50-100 | 1-2 days | .edu email |

**Recommendation**: Apply for **AWS Educate** first (fastest approval), use **Free Tier** to start testing immediately.

---

## Next Steps

After successful EKS deployment:

1. **Compare with Kind**: Run same benchmarks locally vs EKS
2. **Cost Analysis**: Track costs per experiment
3. **Scalability Tests**: Test with different node counts
4. **Multi-Cloud**: Compare AWS vs GCP vs Azure performance

---

## Summary

**To test TriBench on AWS EKS:**

✅ Sign up for AWS Educate ($100 credits, 1-2 days) OR use Free Tier (immediate)  
✅ Install tools: `brew install eksctl kubectl`  
✅ Configure AWS: `aws configure`  
✅ Create cluster: `eksctl create cluster --name tribench-cluster ...` (15-20 min)  
✅ Install metrics-server: `kubectl apply -f ...`  
✅ Update config: `config/hosts/aws-eks.conf`  
✅ Deploy: `tribench sys setup all --kind --config config/hosts/aws-eks.conf`  
✅ Run benchmarks: `tribench exp run ...`  
✅ Cleanup: `eksctl delete cluster --name tribench-cluster`

**Estimated costs: $5-12/day or FREE with Free Tier** 🎉
