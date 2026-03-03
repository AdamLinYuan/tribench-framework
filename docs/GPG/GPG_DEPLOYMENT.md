# TriBench Deployment Guide - GPG Cluster

Guide for deploying TriBench to a single GPG node using Kubernetes (kubeadm).

> **Scope:** This guide covers a single-node setup where you are building the Kubernetes cluster yourself from scratch. You do not need Ceph, Rook, or worker nodes for this. TriBench brings its own storage via MinIO.

## Prerequisites

- SSH access to a GPG node (via DCS SSH gateway)
- `sudo` access on that node
- `kubectl` installed on your local machine
- TriBench installed locally (`pip install -e .`)

## Architecture Overview

```
Your Local Machine
    ↓ SSH Tunnel (port 6443)
GPG Node (gpgnode-20.dcs.gla.ac.uk)  ← single node: control plane + workloads
    └── TriBench Pods
        ├── Trino Coordinator
        ├── MinIO (S3-compatible storage)
        ├── PostgreSQL (Hive Metastore backend)
        └── Hive Metastore (Iceberg catalog)
```

---

## Phase 1: Build the Kubernetes Cluster (on the GPG node)

SSH into your chosen GPG node:

```bash
ssh gpgnode-20.dcs.gla.ac.uk
```

### Step 1.1 — Run the pre-init script

This installs kubeadm, kubelet, kubectl and configures system prerequisites (disables swap, loads kernel modules, sets sysctl params). Run as your own user — it uses `sudo` internally:

```bash
bash scripts/k8s_preinit.sh
```

### Step 1.2 — Move containerd storage to scratch2

By default containerd stores images under `/var/lib/containerd` on the root partition, which is small. Move it to `/scratch2` (the large data disk):

```bash
sudo sed -i 's|^root = .*|root = "/scratch2/containerd"|' /etc/containerd/config.toml
sudo sed -i 's|^state = .*|state = "/scratch2/containerd_state"|' /etc/containerd/config.toml
sudo systemctl daemon-reload
sudo systemctl restart containerd
```

### Step 1.3 — Initialise the cluster

```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16
```

### Step 1.4 — Regenerate the API server certificate with localhost SAN

By default kubeadm does not include `localhost` in the API server certificate, which breaks kubectl when connecting through an SSH tunnel. Regenerate the cert before copying the kubeconfig:

```bash
sudo rm /etc/kubernetes/pki/apiserver.crt /etc/kubernetes/pki/apiserver.key
sudo kubeadm init phase certs apiserver --apiserver-cert-extra-sans=localhost
sudo systemctl restart kubelet
```

### Step 1.5 — Copy kubeconfig to your home directory


GPG sudo cannot write directly to home directories, so use `tee`:

```bash
mkdir -p $HOME/.kube
sudo cat /etc/kubernetes/admin.conf | tee $HOME/.kube/config > /dev/null
chown $(id -u):$(id -g) $HOME/.kube/config
```

### Step 1.6 — Install Calico network plugin

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.3/manifests/calico.yaml

# Watch until all pods show Running before continuing
kubectl get pods --all-namespaces -w
```

### Step 1.7 — Allow workloads on the control plane node

By default Kubernetes prevents pods from running on the control plane. On a single-node setup you must remove this taint:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

---

## Phase 2: Connect from Your Local Machine

### Step 2.1 — Copy and patch kubeconfig locally

```bash
# Pull the kubeconfig from the GPG node
ssh gpgnode-20.dcs.gla.ac.uk "cat ~/.kube/config" > ~/.kube/gpg-config

# Patch the server address to localhost (traffic will go through the SSH tunnel)
sed -i '' 's|server: https://.*:6443|server: https://localhost:6443|g' ~/.kube/gpg-config

# Merge into your main kubeconfig
cp ~/.kube/config ~/.kube/config.backup
KUBECONFIG=~/.kube/config:~/.kube/gpg-config kubectl config view --flatten > ~/.kube/merged
mv ~/.kube/merged ~/.kube/config
chmod 600 ~/.kube/config

# Give the context a friendly name
kubectl config rename-context kubernetes-admin@kubernetes gpg-cluster
kubectl config use-context gpg-cluster
```

### Step 2.2 — Start the SSH tunnel

Open a **dedicated terminal** and keep it running:

```bash
ssh -L 6443:localhost:6443 gpgnode-20.dcs.gla.ac.uk -N
```

### Step 2.3 — Verify access

```bash
kubectl get nodes
# Expected:
# NAME         STATUS   ROLES           AGE   VERSION
# gpgnode-XX   Ready    control-plane   2m    v1.xx.x
```

---

## Phase 3: Configure TriBench

Create `config/hosts/gpg.conf` in the TriBench framework directory:

```hocon
tribench {
  defaults {
    backend = "kubernetes"
  }

  systems {
    kubernetes {
      context = "gpg-cluster"
      namespace = "tribench"
    }

    trino {
      coordinator {
        host = "localhost"
        port = 8080
      }
    }
  }
}
```

Activate the profile:

```bash
tribench config profile set gpg
```

---

## Phase 4: Deploy and Run TriBench

### Step 4.1 — Deploy all systems

```bash
tribench sys setup all
tribench sys start all

# Watch pods come up
kubectl get pods -n tribench -w
```

### Step 4.2 — Load data

```bash
tribench data load --dataset tpch-sf1
```

### Step 4.3 — Run an experiment

```bash
tribench exp run tpch-gpg.yaml --runs 10 --warmup 2
```

### Step 4.4 — View results

```bash
tribench result show tpch-gpg
```

---

## Cleanup

```bash
# Stop TriBench pods
tribench sys stop all

# Full wipe
kubectl delete namespace tribench

# Close SSH tunnel terminal
```

To tear down Kubernetes entirely on the GPG node:

```bash
bash scripts/reset_k8s.sh
```

---

## Troubleshooting

### x509: certificate is valid for gpgnode-20, not localhost
The API server cert doesn't include `localhost` as a SAN. Fix it on the GPG node:
```bash
sudo rm /etc/kubernetes/pki/apiserver.crt /etc/kubernetes/pki/apiserver.key
sudo kubeadm init phase certs apiserver --apiserver-cert-extra-sans=localhost
sudo systemctl restart kubelet
```
Then re-copy the kubeconfig locally (Step 2.1) and retry.

### kubectl times out
Ensure the SSH tunnel is running (`ssh -L 6443:localhost:6443 gpgnode-20.dcs.gla.ac.uk -N`) and that the kubeconfig has `server: https://localhost:6443`.

### Pods stuck in Pending
```bash
kubectl describe pod -n tribench <pod-name>
# Common cause: control-plane taint still set
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

### ImagePullBackOff
The GPG node needs internet access to pull Docker images. Check with the cluster admin if egress is restricted.

### Port 6443 already in use
Another SSH tunnel may already be running: `lsof -i :6443` to find and kill it.

---

## Quick Reference

```bash
# 1. SSH tunnel (keep running)
ssh -L 6443:localhost:6443 gpgnode-20.dcs.gla.ac.uk -N

# 2. Deploy
tribench config profile gpg
tribench sys setup all && tribench sys start all

# 3. Port-forward Trino (keep running in separate terminal)
kubectl port-forward -n tribench svc/tribench-trino 8080:8080

# 4. Load data and run
tribench data load --dataset tpch-sf1
tribench exp run tpch-gpg.yaml

# 5. Results
tribench result show tpch-gpg

# 6. Cleanup
tribench sys stop all
kubectl delete namespace tribench
```


## Architecture Overview

```
Your Local Machine
    ↓ SSH Tunnel
GPG Control Plane (gpgnode-20.dcs.gla.ac.uk)
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
ssh gpgnode-20.dcs.gla.ac.uk
``` Worker nodes are `gpgnode-05`, `gpgnode-06`, etc. Confirm with the cluster admin if this has changed.

### 1.2 Get Kubeconfig

On the GPG control plane node. The kubeconfig was generated by kubeadm and copied to your home directory:

```bash
# View kubeconfig
cat ~/.kube/config
```

Copy the entire content. 

> **Note:** If the cluster was freshly set up and `~/.kube/config` doesn't exist yet, use:
> ```bash
> mkdir -p $HOME/.kube
> sudo cat /etc/kubernetes/admin.conf | tee $HOME/.kube/config > /dev/null
> chown $(id -u):$(id -g) $HOME/.kube/config
> ```
> GPG sudo cannot write directly to home directories, hence using `tee`.

### 1.3 Configure Local kubectl

On your local machine:

```bash
# Save the kubeconfig from GPG
ssh gpgnode-20.dcs.gla.ac.uk "cat ~/.kube/config" > ~/.kube/gpg-config

# IMPORTANT: Patch the server URL to route through the SSH tunnel.
# The kubeconfig will contain the internal IP (e.g. 130.209.255.4);
# replace it with localhost so kubectl goes through the SSH tunnel.
sed -i '' 's|server: https://.*:6443|server: https://localhost:6443|g' ~/.kube/gpg-config

# Merge into your main kubeconfig
cp ~/.kube/config ~/.kube/config.backup
KUBECONFIG=~/.kube/config:~/.kube/gpg-config kubectl config view --flatten > ~/.kube/merged
mv ~/.kube/merged ~/.kube/config
chmod 600 ~/.kube/config

# Give the context a friendly name
kubectl config rename-context kubernetes-admin@kubernetes gpg-cluster

# Switch to it
kubectl config use-context gpg-cluster
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
ssh -L 6443:localhost:6443 gpgnode-20.dcs.gla.ac.uk -N
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
      # Context name after renaming (see Step 1.3)
      # If you skipped the rename, use: kubernetes-admin@kubernetes
      context = "gpg-cluster"
      namespace = "tribench"
      
      # Ceph (rook-cephfs) is available on GPG for persistent storage.
      # Set to false to use emptyDir instead (faster setup, data lost on pod restart).
      use_persistent_volumes = false
      storage_class = "rook-cephfs"  # only used if use_persistent_volumes = true
      
      # Disable Kind cluster creation (cluster already exists)
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

## Step 7: Kubernetes Pod Monitoring

The GPG cluster has **metrics-server and Prometheus** already installed by the cluster admin.

### 7.1 Verify metrics-server

```bash
kubectl get deployment metrics-server -n kube-system
# NAME             READY   UP-TO-DATE   AVAILABLE   AGE
# metrics-server   1/1     1            1           30d

# Test it works
kubectl top nodes
kubectl top pods -n tribench
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

### 7.3 Access Prometheus

Prometheus is installed in the `monitoring` namespace. Access it via SSH tunnel:

```bash
# Terminal 1: forward Prometheus from gpgnode to your laptop
ssh -L 9090:localhost:9090 gpgnode-20.dcs.gla.ac.uk -N &

# Terminal 2: forward the port-forward from kubectl to gpgnode
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
```

Then open `http://localhost:9090` in your browser.

> **Note:** Kepler (energy/power metrics per pod) is also installed. It appears in Prometheus under `serviceMonitor/monitoring/kepler-monitor`.

### 7.4 Enable Monitoring in Experiments

TriBench will automatically collect pod metrics via metrics-server:

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
scp gpgnode-20.dcs.gla.ac.uk:/path/to/tribench-framework/results/tribench.db ./results/
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
1. Ensure SSH tunnel is running (`ssh -L 6443:localhost:6443 gpgnode-20.dcs.gla.ac.uk -N`)
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
| **Storage** | Local volumes | GKE default SC | Ceph (rook-cephfs) or emptyDir |
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
ssh -L 6443:localhost:6443 gpgnode-20.dcs.gla.ac.uk -N

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
- **Cluster Admin:** Youssef Moawad (see cluster setup guide) or check with your supervisor
- **TriBench Issues:** See main README.md

---

## Appendix: Rebuilding the Cluster (Admin Only)

This section is only relevant if the cluster needs to be rebuilt from scratch. Requires `sudo` on all nodes.

### On every node (control plane + workers)

```bash
# Run the pre-init script to install kubeadm/kubelet/kubectl,
# disable swap, load kernel modules, configure sysctl
bash scripts/k8s_preinit.sh

# Change containerd image storage to the larger scratch2 partition
sudo sed -i 's|^root = .*|root = "/scratch2/containerd"|' /etc/containerd/config.toml
sudo sed -i 's|^state = .*|state = "/scratch2/containerd_state"|' /etc/containerd/config.toml
sudo systemctl daemon-reload && sudo systemctl restart containerd
```

### On the control plane node only

```bash
# Initialise the cluster
sudo kubeadm init --pod-network-cidr=192.168.0.0/16

# Copy kubeconfig (tee required because sudo can't write to home dir)
mkdir -p $HOME/.kube
sudo cat /etc/kubernetes/admin.conf | tee $HOME/.kube/config > /dev/null
chown $(id -u):$(id -g) $HOME/.kube/config

# Install Calico network plugin
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.3/manifests/calico.yaml

# Wait for all pods to be Running, then print the worker join command
kubectl get pods --all-namespaces -w
sudo kubeadm token create --print-join-command
```

### On each worker node

Run the join command printed above.

### Storage (Ceph via Rook)

Ceph provides `rook-cephfs` as a StorageClass for persistent volumes. To set it up, clone the Rook repo and apply:

```bash
git clone --single-branch --branch v1.16.6 https://github.com/rook/rook.git
cd rook/deploy/examples
kubectl apply -f crds.yaml -f common.yaml -f operator.yaml -f cluster.yaml
```

Each worker node needs an unmounted partition (`/dev/sdb2`) pre-created for Ceph OSDs. See the full cluster setup guide for partition and wipe steps.

> TriBench does not require Ceph — it uses MinIO as its own object store. Ceph is only needed if you want persistent volumes that survive pod restarts.
