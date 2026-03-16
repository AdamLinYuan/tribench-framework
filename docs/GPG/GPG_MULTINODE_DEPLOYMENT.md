# TriBench Multi-Node Deployment — GPG Cluster

Guide for deploying TriBench across multiple GPG nodes using kubeadm, with one
control plane node and one or more worker nodes. This enables running Trino with
genuine distributed workers rather than a single-node simulation.

> **See also:** [GPG_DEPLOYMENT.md](GPG_DEPLOYMENT.md) for the single-node baseline.

---

## Architecture Overview

```
Your Local Machine
    ↓ SSH Tunnel (port 6443 → control plane)
gpgnode-13  ← control plane + Trino coordinator / MinIO / Hive / PostgreSQL
gpgnode-14  ← worker node: Trino worker-1
gpgnode-15  ← worker node: Trino worker-2  (optional, add more the same way)
```

All nodes must be reachable from each other by hostname within the DCS network.
GPG nodes on the same subnet can communicate directly — no special configuration
is needed beyond what kubeadm sets up.

---

## Prerequisites

- SSH access to **all** GPG nodes you intend to use
- `sudo` access on all nodes
- `kubectl` installed on your **local machine**
- TriBench installed locally (`pip install -e .`)
- The single-node setup completed first on the control plane node (see
  [GPG_DEPLOYMENT.md](GPG_DEPLOYMENT.md)) — or follow Phase 1 below from
  scratch choosing the multi-node path

---

## Phase 1: Prepare All Nodes

Run the following steps **on every node** (control plane and each worker).

### Step 1.1 — Run the pre-init script on each node

Open a separate terminal per node and run:

```bash
ssh gpgnode-13.dcs.gla.ac.uk   # control plane
bash scripts/k8s_preinit.sh

ssh gpgnode-14.dcs.gla.ac.uk   # worker 1
bash scripts/k8s_preinit.sh

# repeat for further worker nodes …
```

### Step 1.2 — Move containerd storage to scratch2 on each node

```bash
sudo sed -i 's|^root = .*|root = "/scratch2/containerd"|' /etc/containerd/config.toml
sudo sed -i 's|^state = .*|state = "/scratch2/containerd_state"|' /etc/containerd/config.toml
sudo systemctl daemon-reload
sudo systemctl restart containerd
```

Run this on **every** node before initialising the cluster.

---

## Phase 2: Initialise the Control Plane

SSH into the designated control plane node (e.g. `gpgnode-13`).

### Step 2.1 — Initialise kubeadm

```bash
sudo kubeadm init \
  --pod-network-cidr=192.168.0.0/16 \
  --apiserver-advertise-address=<gpgnode-13-internal-ip>
```

Replace `<gpgnode-13-internal-ip>` with the node's actual IP (find it with
`hostname -I | awk '{print $1}'`). This ensures the API server advertises the
right address to worker nodes joining the cluster.

### Step 2.2 — Regenerate the API server certificate with localhost SAN

Required so that the SSH tunnel from your laptop works:

```bash
sudo rm /etc/kubernetes/pki/apiserver.crt /etc/kubernetes/pki/apiserver.key
sudo kubeadm init phase certs apiserver \
  --apiserver-cert-extra-sans=localhost,<gpgnode-13-internal-ip>
sudo systemctl restart kubelet
```

### Step 2.3 — Copy kubeconfig on the control plane node

```bash
mkdir -p $HOME/.kube
sudo cat /etc/kubernetes/admin.conf | tee $HOME/.kube/config > /dev/null
chown $(id -u):$(id -g) $HOME/.kube/config
```

### Step 2.4 — Install network plugin (Calico)

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.3/manifests/calico.yaml

# Wait until all calico pods are Running before continuing
kubectl get pods -n kube-system -w
```

### Step 2.5 — Save the join command

kubeadm printed a `kubeadm join` command at the end of `init`. Save it — you
will need it for each worker. It looks like:

```
kubeadm join <ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

If you lost it, regenerate it:

```bash
kubeadm token create --print-join-command
```

---

## Phase 3: Join Worker Nodes

SSH into each worker node and run the join command **with `sudo`**:

```bash
ssh gpgnode-14.dcs.gla.ac.uk
sudo kubeadm join <control-plane-ip>:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```

Repeat for each additional worker.

Verify from the **control plane**:

```bash
kubectl get nodes
# NAME         STATUS   ROLES           AGE   VERSION
# gpgnode-13   Ready    control-plane   5m    v1.xx.x
# gpgnode-14   Ready    <none>          1m    v1.xx.x
# gpgnode-15   Ready    <none>          1m    v1.xx.x
```

---

## Phase 4: Configure Node Roles and Scheduling

### Step 4.1 — Label worker nodes

TriBench uses node labels to pin Trino workers to specific nodes. Label each
worker:

```bash
kubectl label node gpgnode-14 tribench-role=trino-worker
kubectl label node gpgnode-15 tribench-role=trino-worker
```

Label the control plane node for the coordinator and infrastructure pods:

```bash
kubectl label node gpgnode-13 tribench-role=coordinator
```

### Step 4.2 — Allow workloads on control plane

On a multi-node cluster the control plane taint should still be removed so that
MinIO, PostgreSQL and Hive Metastore can schedule there alongside the Trino
coordinator:

```bash
kubectl taint nodes gpgnode-13 node-role.kubernetes.io/control-plane-
```

> **Note:** Worker nodes never have this taint so no action is needed for them.

---

## Phase 5: Connect from Your Local Machine

### Step 5.1 — Copy and patch kubeconfig

```bash
# Pull the kubeconfig from the control plane node
ssh gpgnode-13.dcs.gla.ac.uk "cat ~/.kube/config" > ~/.kube/gpg-multinode-config

# Patch server address to go through the SSH tunnel
sed -i '' 's|server: https://.*:6443|server: https://localhost:6443|g' \
  ~/.kube/gpg-multinode-config

# Merge into your main kubeconfig
cp ~/.kube/config ~/.kube/config.backup
KUBECONFIG=~/.kube/config:~/.kube/gpg-multinode-config \
  kubectl config view --flatten > ~/.kube/merged
mv ~/.kube/merged ~/.kube/config
chmod 600 ~/.kube/config

# Name the context
kubectl config rename-context kubernetes-admin@kubernetes gpg-multinode
kubectl config use-context gpg-multinode
```

### Step 5.2 — Start the SSH tunnel

Traffic only needs to reach the **control plane**:

```bash
ssh -L 6443:localhost:6443 gpgnode-13.dcs.gla.ac.uk -N
```

Keep this terminal open for the duration of your session.

### Step 5.3 — Verify access

```bash
kubectl get nodes
# All nodes should show Ready
```

---

## Phase 6: Configure TriBench

Create `config/hosts/gpg-multinode.conf`:

```hocon
tribench {
  defaults {
    backend = "kubernetes"
  }

  systems {
    hive_metastore {
      kubernetes {
        image = "adamlinyuan/hive-metastore:4.0.0-amd64"
        imagePullPolicy = "IfNotPresent"
      }
    }

    trino {
      coordinator {
        jvm {
          heap = "16G"
        }
      }

      query {
        max_memory = "40GB"         # sum across all workers
        max_memory_per_node = "10GB"
      }

      # One entry per worker node
      workers = [
        { name = "worker-1" }
        { name = "worker-2" }
      ]
    }
  }

  kubernetes {
    context = "gpg-multinode"
    namespace = "tribench"
    use_persistent_volumes = false
    create_cluster = false
  }
}
```

Activate the profile:

```bash
tribench config profile gpg-multinode
tribench config show  # verify context = "gpg-multinode"
```

---

## Phase 7: Deploy and Run TriBench

### Step 7.1 — Deploy all systems

```bash
tribench sys setup all
tribench sys start all
```

Watch pods distribute across nodes:

```bash
kubectl get pods -n tribench -o wide -w
```

You should see Trino workers scheduled on `gpgnode-14`/`gpgnode-15` and the
coordinator + infrastructure pods on `gpgnode-13`.

### Step 7.2 — Load data

```bash
tribench data load tpch-sf1 --schema tpch
```

### Step 7.3 — Run experiments

```bash
tribench exp run experiments/tpch-gpg.yaml --runs 10 --warmup 2
```

### Step 7.4 — View results

```bash
tribench result show tpch-gpg
```

---

## Adding More Worker Nodes Later

You can add nodes to a running cluster without restarting anything.

1. Run `k8s_preinit.sh` on the new node and move containerd to scratch2
   (Steps 1.1–1.2).
2. Generate a fresh join token on the control plane:
   ```bash
   kubeadm token create --print-join-command
   ```
3. Run the join command on the new node.
4. Label it:
   ```bash
   kubectl label node gpgnode-23 tribench-role=trino-worker
   ```
5. Update `workers` in `gpg-multinode.conf` and restart Trino:
   ```bash
   tribench sys stop trino
   tribench sys start trino
   ```

---

## Removing a Worker Node

```bash
# Drain workloads off the node gracefully
kubectl drain gpgnode-15 --ignore-daemonsets --delete-emptydir-data

# Remove from cluster
kubectl delete node gpgnode-15

# On the node itself, reset kubeadm state
ssh gpgnode-15.dcs.gla.ac.uk
sudo kubeadm reset -f
```

---

## Differences from Single-Node Setup

| Aspect | Single Node | Multi-Node |
|---|---|---|
| kubeadm init | no `--apiserver-advertise-address` needed | must specify internal IP |
| Workers | none (coordinator only) | one pod per worker node |
| Node taint | remove from single node | remove only from control plane |
| SSH tunnel | to the one node | to control plane only |
| kubeconfig context | `gpg-cluster` | `gpg-multinode` |
| `max_memory` | 20GB | increase per worker count |

---

## Troubleshooting

### Worker node stays NotReady

Check kubelet status on the worker:
```bash
ssh gpgnode-14.dcs.gla.ac.uk
sudo systemctl status kubelet
sudo journalctl -u kubelet -n 50
```
Most likely cause: swap not disabled or containerd not running. Re-run
`k8s_preinit.sh`.

### Pods stuck in Pending on worker nodes

```bash
kubectl describe pod -n tribench <pod-name>
```
Common cause: Calico not yet running on the worker. Wait for:
```bash
kubectl get pods -n kube-system -o wide | grep calico-node
```
All calico-node pods (one per node) must show `Running`.

### kubeadm join token expired

Tokens expire after 24 hours. Generate a new one on the control plane:
```bash
kubeadm token create --print-join-command
```

### Cannot contact API server from worker node

The worker must be able to reach the control plane's internal IP on port 6443.
Test from the worker:
```bash
curl -sk https://<control-plane-ip>:6443/healthz
# Should return: ok
```
If it fails, check the university firewall or contact DCS support.

### Trino workers failing to connect to coordinator

Verify all pods are in `Running` and `Ready` state:
```bash
kubectl get pods -n tribench -o wide
```
Check Trino coordinator logs for registration errors:
```bash
kubectl logs -n tribench deployment/trino-coordinator | grep -i "worker\|node\|register"
```
