# Configuration Guide

**TriBench Configuration System**  
**Last Updated**: January 8, 2026

---

## Overview

TriBench uses a hierarchical configuration system that allows flexible deployment across different environments (local, GCP, Azure, AWS) without code changes. Configuration values are resolved using a priority chain where higher-priority sources override lower ones.

---

## Configuration Priority

Values are resolved in this order (highest to lowest priority):

1. **Environment Variables** (highest priority)
2. **Configuration Files** (via `--config` flag or auto-detected)
3. **Hardcoded Defaults** (fallback in `lib/tribench/defaults.py`)

### Example Priority Resolution

```bash
# Scenario: All three levels specify a value
export TRIBENCH_K8S_CONTEXT="env-context"          # Priority 1 (ENV)
# config/hosts/gcp-gke.conf has: context = "gke-context"  # Priority 2 (Config)
# defaults.py has: CONTEXT = "kind-tribench"       # Priority 3 (Default)

# Result: Uses "env-context" (ENV wins)
```

---

## Environment Variables

### Kubernetes Configuration

#### `TRIBENCH_K8S_CONTEXT`
**Purpose**: Override the Kubernetes context  
**Default**: `kind-tribench`  
**Usage**:
```bash
# Switch to GKE
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"

# Switch to AKS
export TRIBENCH_K8S_CONTEXT="aks-tribench-cluster"

# Switch to EKS
export TRIBENCH_K8S_CONTEXT="arn:aws:eks:us-east-1:123456789012:cluster/tribench"

# Use local Kind cluster (default)
unset TRIBENCH_K8S_CONTEXT
```

#### `TRIBENCH_K8S_NAMESPACE`
**Purpose**: Override the Kubernetes namespace  
**Default**: `tribench`  
**Usage**:
```bash
export TRIBENCH_K8S_NAMESPACE="production"
export TRIBENCH_K8S_NAMESPACE="staging"
```

### Usage Examples

**Example 1: Deploy to GKE without modifying code**
```bash
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"
tribench sys setup all --kind
tribench exp run experiments/tpch-k8s-monitored.yaml
```

**Example 2: Switch between environments**
```bash
# Development on local Kind
unset TRIBENCH_K8S_CONTEXT
tribench sys status --kind  # Uses kind-tribench

# Production on GKE
export TRIBENCH_K8S_CONTEXT="gke_prod_us-central1-a_tribench-prod"
tribench sys status --kind  # Uses GKE cluster
```

**Example 3: CI/CD Pipeline**
```yaml
# .github/workflows/test.yml
jobs:
  test-gke:
    steps:
      - name: Set GKE context
        run: echo "TRIBENCH_K8S_CONTEXT=${{ secrets.GKE_CONTEXT }}" >> $GITHUB_ENV
      
      - name: Run benchmarks
        run: tribench exp run experiments/tpch-k8s-monitored.yaml
```

---

## Configuration Files

### File Locations

TriBench searches for configuration files in this order:

1. **Explicit config**: Specified via `--config` flag
2. **Host-specific config**: `config/hosts/$(hostname).conf`
3. **Reference config**: `config/reference.conf` (always loaded as base)

### Host-Specific Configurations

Create configuration files for specific deployment environments:

**`config/hosts/gcp-gke.conf`** - Google Cloud (GKE)
```hocon
tribench {
  systems {
    kubernetes {
      context = "gke_tribench_us-central1-a_tribench-cluster"
      namespace = "tribench"
      timeout = 600  # Cloud pods may take longer
    }
  }
}
```

**`config/hosts/azure-aks.conf`** - Azure (AKS)
```hocon
tribench {
  systems {
    kubernetes {
      context = "aks-tribench-cluster"
      namespace = "tribench"
    }
  }
}
```

**`config/hosts/aws-eks.conf`** - AWS (EKS)
```hocon
tribench {
  systems {
    kubernetes {
      context = "arn:aws:eks:us-east-1:123456789012:cluster/tribench"
      namespace = "tribench"
    }
  }
}
```

### Using Configuration Files

**Option 1: Explicit config file**
```bash
tribench sys setup all --kind --config config/hosts/gcp-gke.conf
```

**Option 2: Hostname-based auto-detection**
```bash
# Create config/hosts/$(hostname).conf
# TriBench will automatically load it
tribench sys setup all --kind
```

**Option 3: Environment variable + config file**
```bash
# ENV variable overrides config file
export TRIBENCH_K8S_CONTEXT="override-context"
tribench sys setup all --kind --config config/hosts/gcp-gke.conf
# Uses: "override-context" (not the one in config file)
```

---

## Cloud Provider Detection

TriBench automatically detects the cloud provider from the context name:

| Context Pattern | Provider | Example |
|----------------|----------|---------|
| `kind-*` | Local Kind | `kind-tribench` |
| `gke_*` | Google Cloud (GKE) | `gke_tribench_us-central1-a_tribench-cluster` |
| `aks-*` | Azure (AKS) | `aks-tribench-cluster` |
| `arn:aws:eks:*` | AWS (EKS) | `arn:aws:eks:us-east-1:123456789012:cluster/tribench` |
| `docker-desktop` | Docker Desktop | `docker-desktop` |

---

## Common Configuration Patterns

### Pattern 1: Local Development
```bash
# Use defaults (Kind cluster)
tribench sys setup all --kind
tribench sys status --kind
```

### Pattern 2: Cloud Testing
```bash
# Set context via environment variable
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"
tribench sys setup all --kind
```

### Pattern 3: Multi-Environment Setup
```bash
# Production
export TRIBENCH_ENV=production
export TRIBENCH_K8S_CONTEXT="gke_prod_us-central1-a_tribench-prod"
export TRIBENCH_K8S_NAMESPACE="production"

# Staging
export TRIBENCH_ENV=staging
export TRIBENCH_K8S_CONTEXT="gke_staging_us-central1-a_tribench-staging"
export TRIBENCH_K8S_NAMESPACE="staging"
```

### Pattern 4: Configuration Files Per Environment
```bash
# Directory structure:
config/hosts/
  local-dev.conf       # Local development
  gcp-staging.conf     # GCP staging
  gcp-production.conf  # GCP production
  aws-production.conf  # AWS production

# Usage:
tribench sys setup all --kind --config config/hosts/gcp-production.conf
```

---

## Troubleshooting

### Issue: Commands use wrong context

**Check current context resolution:**
```python
python3 << 'EOF'
import sys
import os
sys.path.insert(0, 'lib')
from tribench.defaults import Defaults

print(f"ENV: {os.getenv('TRIBENCH_K8S_CONTEXT')}")
print(f"Default: {Defaults.Kubernetes.CONTEXT}")
print(f"Result: {Defaults.Kubernetes.get_context()}")
EOF
```

**Verify kubectl context:**
```bash
kubectl config get-contexts
kubectl config current-context
```

### Issue: Context not found

**List available contexts:**
```bash
kubectl config get-contexts -o name
```

**Get GKE credentials:**
```bash
gcloud container clusters get-credentials tribench-cluster --zone us-central1-a
```

**Get AKS credentials:**
```bash
az aks get-credentials --resource-group tribench-rg --name tribench-cluster
```

**Get EKS credentials:**
```bash
aws eks update-kubeconfig --region us-east-1 --name tribench-cluster
```

### Issue: Config file not loading

**Check config file syntax:**
```bash
# HOCON syntax validator
python3 << 'EOF'
from pyhocon import ConfigFactory
config = ConfigFactory.parse_file('config/hosts/gcp-gke.conf')
print(config)
EOF
```

**Verify config file path:**
```bash
ls -la config/hosts/*.conf
```

---

## Configuration Schema

### Kubernetes System Configuration

```hocon
tribench {
  systems {
    kubernetes {
      # Required
      context = "kind-tribench"        # Kubernetes context name
      namespace = "tribench"            # Kubernetes namespace
      
      # Optional
      timeout = 600                     # Deployment timeout (seconds)
      storage_class = "standard"        # Storage class for PVCs
    }
  }
}
```

### Experiment Configuration

```hocon
experiment {
  monitoring {
    kubernetes {
      enabled = true
      context = "gke_tribench_us-central1-a_tribench-cluster"
      namespace = "tribench"
      interval_seconds = 5
      pod_filters = {
        labels = { app = "trino" }
        pattern = "trino-.*"
      }
    }
  }
}
```

---

## Best Practices

### 1. Use Environment Variables for Dynamic Contexts
```bash
# Good: Easy to switch
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"

# Avoid: Modifying code or config files for temporary switches
```

### 2. Create Host-Specific Configs
```bash
# Good: One config per environment
config/hosts/
  dev-laptop.conf
  gcp-prod.conf
  aws-staging.conf

# Avoid: Modifying reference.conf
```

### 3. Document Your Contexts
```bash
# Create a contexts.md file
kubectl config get-contexts > docs/available-contexts.md
```

### 4. Use Descriptive Context Names
```bash
# Good
gke_tribench_us-central1-a_tribench-prod
aks-tribench-staging-eastus

# Less clear
my-cluster
test123
```

### 5. Automate Context Setup
```bash
# Add to your shell profile (.bashrc, .zshrc)
alias tribench-local="unset TRIBENCH_K8S_CONTEXT"
alias tribench-gke="export TRIBENCH_K8S_CONTEXT='gke_tribench_us-central1-a_tribench-cluster'"
alias tribench-aws="export TRIBENCH_K8S_CONTEXT='arn:aws:eks:us-east-1:123456789012:cluster/tribench'"
```

---

## Reference

### All Kubernetes Environment Variables

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `TRIBENCH_K8S_CONTEXT` | Kubernetes context | `kind-tribench` | `gke_tribench_us-central1-a_tribench-cluster` |
| `TRIBENCH_K8S_NAMESPACE` | Kubernetes namespace | `tribench` | `production` |

### Configuration File Format

TriBench uses **HOCON** (Human-Optimized Config Object Notation) format:
- Superset of JSON
- Supports comments (`#` or `//`)
- Supports variable substitution: `${tribench.app.path.home}`
- Supports includes: `include "base.conf"`

### Related Documentation

- [GCP Deployment Guide](journal/04_phase_4_cloud_deployment_gcp.md)
- [Configuration Fix Plan](CONFIG_FIX_PLAN.md)
- [Host Configs](../config/hosts/README.md)

---

**Questions or Issues?**  
See [CONFIG_FIX_PLAN.md](CONFIG_FIX_PLAN.md) for implementation details or open an issue on GitHub.
