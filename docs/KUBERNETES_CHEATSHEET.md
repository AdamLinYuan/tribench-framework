# Kubernetes Quick Reference for Phase 4.1

## Essential Commands

### Cluster Management
```bash
# Create kind cluster
kind create cluster --name tribench --config config/kubernetes/kind-cluster-config.yaml

# List clusters
kind get clusters

# Delete cluster
kind delete cluster --name tribench

# Get cluster info
kubectl cluster-info --context kind-tribench
```

### Context & Namespace
```bash
# List contexts
kubectl config get-contexts

# Switch context
kubectl config use-context kind-tribench

# Set default namespace
kubectl config set-context --current --namespace=default

# Create namespace
kubectl create namespace tribench
```

### Pods
```bash
# List all pods
kubectl get pods

# Get pods with labels
kubectl get pods -l app=trino

# Describe pod (detailed info)
kubectl describe pod <pod-name>

# Get pod logs
kubectl logs <pod-name>

# Follow logs (like tail -f)
kubectl logs -f <pod-name>

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/bash

# Port forward to pod
kubectl port-forward pod/<pod-name> 8080:8080
```

### Services
```bash
# List services
kubectl get services
kubectl get svc

# Describe service
kubectl describe svc <service-name>

# Port forward to service
kubectl port-forward svc/trino-coordinator 8080:8080
```

### Deployments & StatefulSets
```bash
# List deployments
kubectl get deployments
kubectl get deploy

# List statefulsets
kubectl get statefulsets
kubectl get sts

# Scale deployment
kubectl scale deployment trino-coordinator --replicas=2

# Restart deployment (rolling restart)
kubectl rollout restart deployment trino-coordinator

# Check rollout status
kubectl rollout status deployment trino-coordinator
```

### ConfigMaps & Secrets
```bash
# List configmaps
kubectl get configmaps
kubectl get cm

# View configmap
kubectl describe cm trino-config

# List secrets
kubectl get secrets

# View secret (base64 encoded)
kubectl get secret <secret-name> -o yaml
```

### Resource Monitoring
```bash
# Get node resources
kubectl top nodes

# Get pod resources (requires metrics-server)
kubectl top pods

# Get pod resources with labels
kubectl top pods -l app=trino

# Describe node (see allocatable resources)
kubectl describe node
```

### Debugging
```bash
# Get events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check pod why it's not running
kubectl describe pod <pod-name> | grep -A 10 Events

# Check logs of previous container (if pod restarted)
kubectl logs <pod-name> --previous

# Run debug pod
kubectl run debug --image=busybox --rm -it -- /bin/sh

# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup trino-coordinator
```

## Helm Commands

### Repository Management
```bash
# Add Helm repositories
helm repo add trinodb https://trinodb.github.io/charts
helm repo add minio https://charts.min.io/
helm repo add bitnami https://charts.bitnami.com/bitnami

# Update repositories
helm repo update

# Search for charts
helm search repo trino
```

### Release Management
```bash
# Install chart
helm install trino trinodb/trino -f values.yaml

# Upgrade release
helm upgrade trino trinodb/trino -f values.yaml

# Install or upgrade (idempotent)
helm upgrade --install trino trinodb/trino -f values.yaml

# List releases
helm list
helm ls

# Get release values
helm get values trino

# Get release manifest
helm get manifest trino

# Uninstall release
helm uninstall trino

# Rollback release
helm rollback trino 1
```

### Chart Information
```bash
# Show chart info
helm show chart trinodb/trino

# Show chart values (defaults)
helm show values trinodb/trino

# Show all info
helm show all trinodb/trino
```

## Kubernetes DNS

### Service DNS Names
```
# Within same namespace
<service-name>

# Cross-namespace
<service-name>.<namespace>

# Fully qualified
<service-name>.<namespace>.svc.cluster.local
```

### Examples
```bash
# Trino coordinator (same namespace)
trino-coordinator:8080

# Trino coordinator (full)
trino-coordinator.default.svc.cluster.local:8080

# MinIO (same namespace)
minio:9000

# PostgreSQL (same namespace)
postgresql:5432
```

## Common Workflows

### Deploy Entire Stack
```bash
# 1. Create cluster
kind create cluster --name tribench --config config/kubernetes/kind-cluster-config.yaml

# 2. Add Helm repos
helm repo add trinodb https://trinodb.github.io/charts
helm repo add minio https://charts.min.io/
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 3. Install MinIO
helm install minio minio/minio \
  --set mode=standalone \
  --set persistence.size=10Gi \
  --set rootUser=admin \
  --set rootPassword=password

# 4. Install PostgreSQL
helm install postgresql bitnami/postgresql \
  --set auth.username=hive \
  --set auth.password=hive \
  --set auth.database=metastore

# 5. Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql --timeout=5m

# 6. Install Trino
helm install trino trinodb/trino -f config/kubernetes/trino-values.yaml

# 7. Wait for Trino to be ready
kubectl wait --for=condition=ready pod -l app=trino --timeout=10m

# 8. Port forward to access
kubectl port-forward svc/trino-coordinator 8080:8080
```

### Check Everything is Running
```bash
# Quick status
kubectl get all

# Detailed pod status
kubectl get pods -o wide

# Check resource usage
kubectl top pods

# Check events for errors
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20
```

### Restart Services
```bash
# Restart Trino coordinator
kubectl rollout restart deployment trino-coordinator

# Restart Trino workers
kubectl rollout restart statefulset trino-worker

# Delete pod (will be recreated automatically)
kubectl delete pod <pod-name>
```

### Access Services from Host

```bash
# Method 1: Port forwarding (temporary)
kubectl port-forward svc/trino-coordinator 8080:8080

# Method 2: NodePort service (persistent)
# Edit service to add type: NodePort
kubectl patch svc trino-coordinator -p '{"spec":{"type":"NodePort"}}'
kubectl get svc trino-coordinator  # Check NodePort number

# Method 3: LoadBalancer (kind with MetalLB)
# Requires MetalLB installation
```

### Clean Up
```bash
# Uninstall all Helm releases
helm uninstall trino minio postgresql

# Delete namespace (if used custom one)
kubectl delete namespace tribench

# Delete kind cluster
kind delete cluster --name tribench
```

## Troubleshooting

### Pod Stuck in Pending
```bash
# Check why
kubectl describe pod <pod-name> | grep -A 10 Events

# Common causes:
# - Insufficient resources
# - PVC not bound
# - Image pull failed

# Check node resources
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### Pod CrashLoopBackOff
```bash
# Check logs
kubectl logs <pod-name>

# Check previous logs
kubectl logs <pod-name> --previous

# Describe pod
kubectl describe pod <pod-name>
```

### Service Not Accessible
```bash
# Check service endpoints
kubectl get endpoints <service-name>

# If no endpoints, pods not matching labels
kubectl get pods --show-labels
kubectl describe svc <service-name>

# Test DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup <service-name>
```

### Image Pull Errors
```bash
# Check image name in pod spec
kubectl get pod <pod-name> -o yaml | grep image:

# Verify image exists
docker pull <image-name>

# Check imagePullSecrets (if private registry)
kubectl describe pod <pod-name> | grep "Image"
```

## Resource Specifications

### CPU
```yaml
# Formats
cpu: "1"      # 1 core
cpu: "100m"   # 100 millicores (0.1 core)
cpu: "2000m"  # 2000 millicores (2 cores)
```

### Memory
```yaml
# Formats
memory: "128Mi"   # 128 Mebibytes
memory: "1Gi"     # 1 Gibibyte
memory: "1024Mi"  # Same as 1Gi
```

### Storage
```yaml
# Formats
storage: "1Gi"    # 1 Gibibyte
storage: "10Gi"   # 10 Gibibytes
storage: "100Mi"  # 100 Mebibytes
```

## Useful Aliases

Add to your `~/.zshrc`:

```bash
# Kubernetes
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgd='kubectl get deploy'
alias kdp='kubectl describe pod'
alias kl='kubectl logs'
alias klf='kubectl logs -f'
alias kex='kubectl exec -it'
alias kpf='kubectl port-forward'

# Helm
alias h='helm'
alias hls='helm list'
alias hi='helm install'
alias hu='helm upgrade'
alias hdel='helm uninstall'

# kind
alias kcc='kind create cluster'
alias kdc='kind delete cluster'
alias klc='kind get clusters'
```

## Next Steps

1. Create kind cluster: `kind create cluster --name tribench`
2. Install metrics-server: `kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`
3. Deploy test pod: `kubectl run nginx --image=nginx`
4. Check it's running: `kubectl get pods`
5. Access it: `kubectl port-forward pod/nginx 8080:80`
6. Visit: http://localhost:8080
7. Clean up: `kubectl delete pod nginx`

**Now you're ready to implement `KubernetesSystem`!**


Sources:

---

## Essential Commands

### Cluster Management
- **Create, delete, info**: Manage your Kubernetes cluster lifecycle.
  - Create: `kind create cluster`
  - Delete: `kind delete cluster`
  - Info: `kubectl cluster-info`
  - [Kubernetes Cluster Concepts](https://kubernetes.io/docs/concepts/cluster-administration/)

### Pod Operations
- **get, logs, exec, port-forward**: Interact with running containers (pods).
  - Get: `kubectl get pods`
  - Logs: `kubectl logs <pod>`
  - Exec: `kubectl exec -it <pod> -- /bin/bash`
  - Port-forward: `kubectl port-forward <pod/service> <local>:<remote>`
  - [Pods Overview](https://kubernetes.io/docs/concepts/workloads/pods/)

### Services, Deployments, StatefulSets
- **Services**: Expose pods to network.
- **Deployments**: Manage stateless app updates.
- **StatefulSets**: Manage stateful apps (stable identity/storage).
  - [Services](https://kubernetes.io/docs/concepts/services-networking/service/)
  - [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
  - [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)

### ConfigMaps and Secrets
- **ConfigMaps**: Store non-sensitive config data.
- **Secrets**: Store sensitive data (passwords, keys).
  - [ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
  - [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)

### Resource Monitoring
- **Monitor CPU/memory usage of nodes/pods**.
  - `kubectl top nodes`
  - `kubectl top pods`
  - [Resource Metrics](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)

### Debugging Techniques
- **Troubleshoot cluster and workloads**.
  - Events: `kubectl get events`
  - Pod details: `kubectl describe pod <pod>`
  - [Debugging Pods](https://kubernetes.io/docs/tasks/debug/debug-application/)

---

## Helm Commands

### Repository Management
- **Add/update Helm chart repositories**.
  - `helm repo add ...`
  - [Helm Repositories](https://helm.sh/docs/helm/helm_repo/)

### Release Lifecycle
- **Install, upgrade, uninstall charts**.
  - Install: `helm install ...`
  - Upgrade: `helm upgrade ...`
  - Uninstall: `helm uninstall ...`
  - [Helm Install/Upgrade](https://helm.sh/docs/helm/helm_install/)
  - [Helm Uninstall](https://helm.sh/docs/helm/helm_uninstall/)

### Chart Inspection
- **View chart info and default values**.
  - `helm show chart ...`
  - `helm show values ...`
  - [Helm Show](https://helm.sh/docs/helm/helm_show/)

---

## Kubernetes DNS

### Service Naming Conventions
- **How services are addressed inside the cluster**.
  - `<service>.<namespace>.svc.cluster.local`
  - [DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)

### Cross-Namespace References
- **Access services in other namespaces**.
  - Use full DNS name: `<service>.<namespace>.svc.cluster.local`

### Real Examples for Your Stack
- **How TriBench components communicate**.
  - Trino coordinator: `trino-coordinator.default.svc.cluster.local:8080`
  - MinIO: `minio.default.svc.cluster.local:9000`

---

## Getting Started

- [Kubernetes Basics Interactive Tutorial](https://kubernetes.io/docs/tutorials/kubernetes-basics/)
- [Helm Official Docs](https://helm.sh/docs/)
- [Kubernetes Concepts](https://kubernetes.io/docs/concepts/)

These links and explanations will help you understand the core ideas before you start development. Let me know if you want a deeper dive into any topic!