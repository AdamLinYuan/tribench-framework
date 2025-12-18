# Configuration Directory

This directory contains hierarchical configuration files for TriBench framework.

## Structure

```
config/
├── hosts/                      # Host-specific configurations
│   └── localhost/             # Local development environment
│       └── application.conf   # Localhost config overrides
├── templates/                  # Jinja2 templates for system configs
│   ├── trino-config.properties.j2  # Trino config template
│   └── trino-jvm.config.j2        # Trino JVM template
├── fixtures/                   # Test fixtures
│   ├── systems.yaml           # System definitions
│   ├── datasets.yaml          # Dataset definitions
│   └── experiments.yaml       # Experiment templates
└── reference.conf             # Default framework configuration
```

## Configuration Hierarchy

TriBench uses a three-layer hierarchical configuration system:

1. **Reference Config** (`reference.conf`) - Framework defaults
   - System versions (Trino 434, PostgreSQL 15, MinIO)
   - Default ports and endpoints
   - Resource limits
   - Framework paths

2. **Host Config** (`hosts/<hostname>/application.conf`) - Machine-specific overrides
   - Custom installation paths
   - Resource allocations based on hardware
   - Local development shortcuts
   - Auto-detected using hostname

3. **Experiment Config** (`experiments/*.yaml`) - Experiment-specific settings
   - Query selection and parameters
   - Dataset configuration
   - Execution settings (runs, warmup, timeout)
   - System configuration overrides

**Merging**: Later layers override earlier layers, with nested values properly merged.

## Usage

### Load Configuration

```python
from tribench.utils.config import ConfigurationLoader

# Load all layers (reference + host + experiment)
loader = ConfigurationLoader()
config = loader.load(experiment_config="experiments/tpch-sf1.yaml")

# Access values
trino_port = config["tribench"]["systems"]["trino"]["coordinator"]["port"]
```

### Generate System Configs

```python
from tribench.utils.config import ConfigurationTemplate

# Generate Trino configuration from template
template_gen = ConfigurationTemplate()
trino_config = template_gen.generate(
    "trino-config.properties.j2",
    config,
    output_path="systems/trino/etc/config.properties"
)
```

## Configuration Format

TriBench uses **HOCON** (Human-Optimized Config Object Notation) format:

```hocon
# Comments are supported
tribench {
    version = "1.0.0"  # Simple values
    
    # Nested structures
    systems {
        trino {
            port = 8080
            memory = "2G"
        }
    }
    
    # Variable substitution
    paths {
        root = "/opt/tribench"
        logs = ${tribench.paths.root}/log
    }
    
    # Environment variables
    database {
        password = ${DB_PASSWORD}         # Required
        host = ${?DB_HOST}                # Optional
    }
}
```

## Host Configurations

Host-specific configurations allow you to customize TriBench for your specific machine without modifying the framework defaults.

### Quick Start: Create Your Own Host Config

1. **Find your hostname:**
   ```bash
   hostname
   # Example output: macbook-pro.local or dev-server
   ```

2. **Create your host directory:**
   ```bash
   mkdir -p config/hosts/$(hostname)
   ```

3. **Create `application.conf` in your host directory:**
   ```bash
   touch config/hosts/$(hostname)/application.conf
   ```

4. **Start with this template:**
   ```hocon
   # config/hosts/<your-hostname>/application.conf
   # Host-specific configuration overrides
   
   tribench {
     # Override system resource allocations
     systems {
       trino {
         coordinator {
           jvm.heap = "4G"  # Adjust based on your RAM
           port = 8080      # Change if port conflicts
         }
       }
       
       postgresql {
         # Override default credentials for local dev
         username = "myuser"
         password = "mypassword"
       }
       
       minio {
         # Use different ports if needed
         port = 9000
         console_port = 9001
       }
     }
     
     # Custom paths for your machine
     app.path {
       # Use /tmp for temporary data on dev machines
       downloads = "/tmp/tribench/downloads"
       systems = "/tmp/tribench/systems"
       
       # Or use custom directories
       # datasets = "/mnt/data/tribench/datasets"
       # results = "/home/user/tribench-results"
     }
     
     # Kubernetes settings (if using K8s)
     kubernetes {
       context = "docker-desktop"  # or "kind-tribench" or your cluster name
       namespace = "tribench"
     }
   }
   ```

5. **Test your configuration:**
   ```bash
   tribench config show  # View merged configuration
   tribench config validate  # Check for errors
   ```

### Common Customization Scenarios

#### Scenario 1: Developer Laptop (Limited Resources)
```hocon
tribench {
  systems {
    trino {
      coordinator.jvm.heap = "2G"  # Lower memory usage
    }
  }
  
  # Use local temp directories
  app.path {
    downloads = "/tmp/tribench/downloads"
    systems = "/tmp/tribench/systems"
  }
  
  # Smaller datasets for testing
  datasets {
    tpch.scale_factors = ["tiny"]
  }
}
```

#### Scenario 2: High-Performance Server
```hocon
tribench {
  systems {
    trino {
      coordinator.jvm.heap = "16G"  # More RAM available
      
      # Add worker nodes
      workers = [
        { host = "worker1", jvm.heap = "32G" }
        { host = "worker2", jvm.heap = "32G" }
      ]
    }
  }
  
  # Use dedicated storage
  app.path {
    datasets = "/mnt/nvme/tribench/datasets"
    systems = "/opt/tribench/systems"
  }
  
  # Run more experiments in parallel
  execution.parallel_experiments = 4
}
```

#### Scenario 3: Remote Cluster (Kubernetes)
```hocon
tribench {
  kubernetes {
    context = "gke_my-project_us-central1_tribench-cluster"
    namespace = "tribench-prod"
  }
  
  systems {
    trino {
      # Use Helm chart for deployment
      helm_chart = "trinodb/trino"
      helm_release = "tribench-trino"
    }
  }
  
  # Store results in cloud database
  database.results {
    url = "jdbc:postgresql://cloudsql-proxy:5432/tribench"
    username = ${CLOUD_DB_USER}
    password = ${CLOUD_DB_PASSWORD}
  }
}
```

#### Scenario 4: Custom Port Assignments
```hocon
tribench {
  systems {
    trino {
      coordinator.port = 9080  # Avoid conflict with other services
    }
    
    minio {
      port = 19000           # Custom MinIO API port
      console_port = 19001   # Custom console port
    }
    
    postgresql {
      port = 15432           # Custom PostgreSQL port
    }
    
    hive_metastore {
      port = 19083           # Custom Hive Metastore port
    }
  }
}
```

### Using Environment Variables

For sensitive data or deployment-specific values, use environment variables:

```hocon
tribench {
  systems {
    minio {
      # Required: Must be set in environment
      access_key = ${MINIO_ACCESS_KEY}
      secret_key = ${MINIO_SECRET_KEY}
    }
    
    postgresql {
      # Optional: Use default if not set
      host = ${?POSTGRES_HOST}
      password = ${?POSTGRES_PASSWORD}
    }
  }
  
  database.results {
    # Mix of env vars and defaults
    url = "jdbc:postgresql://"${?DB_HOST:-localhost}":5432/tribench"
    username = ${?RESULTS_DB_USER:-tribench}
    password = ${RESULTS_DB_PASSWORD}  # Required
  }
}
```

Set environment variables before running:
```bash
export MINIO_ACCESS_KEY="my-access-key"
export MINIO_SECRET_KEY="my-secret-key"
export RESULTS_DB_PASSWORD="secure-password"

tribench experiment run my-experiment.yaml
```

### Framework Defaults Reference

All framework defaults are defined in `lib/tribench/defaults.py` and documented in `reference.conf`. Here are the key defaults you might want to override:

| Setting | Default | Override In |
|---------|---------|-------------|
| Trino host | `localhost` | `tribench.systems.trino.coordinator.host` |
| Trino port | `8080` | `tribench.systems.trino.coordinator.port` |
| Trino user | `tribench` | `tribench.systems.trino.coordinator.user` |
| MinIO host | `localhost` | `tribench.systems.minio.host` |
| MinIO port | `9000` | `tribench.systems.minio.port` |
| PostgreSQL host | `localhost` | `tribench.systems.postgresql.host` |
| PostgreSQL port | `5432` | `tribench.systems.postgresql.port` |
| K8s context | `kind-tribench` | `tribench.kubernetes.context` |
| K8s namespace | `tribench` | `tribench.kubernetes.namespace` |
| Query timeout | `300s` | `tribench.execution.query.timeout` |
| Max retries | `3` | `tribench.execution.max_retries` |

See `reference.conf` → `tribench.defaults` section for the complete list.

### Configuration Precedence

Configurations are merged in this order (lowest to highest priority):

1. **Code defaults** (`lib/tribench/defaults.py`) - Hard-coded fallbacks
2. **Reference config** (`config/reference.conf`) - Framework defaults
3. **Host config** (`config/hosts/<hostname>/application.conf`) - Your overrides
4. **Experiment config** (`experiments/<name>.yaml`) - Experiment-specific
5. **Environment variables** - Runtime overrides

Example:
```hocon
# reference.conf: port = 8080
# hosts/laptop/application.conf: port = 9080
# experiment.yaml: port = 8888
# Result: port = 8888 (experiment wins)
```

### Validation and Debugging

**View merged configuration:**
```bash
tribench config show
tribench config show --section systems.trino
```

**Validate configuration:**
```bash
tribench config validate
tribench config validate --experiment experiments/my-test.yaml
```

**Debug configuration loading:**
```bash
tribench --verbose config show  # Shows which files are loaded
```

**Check for conflicts:**
```bash
# See which config file sets a specific value
tribench config trace tribench.systems.trino.coordinator.port
```

### Best Practices

1. **Start small**: Copy only the sections you need to override from `reference.conf`
2. **Add comments**: Explain why you're overriding a setting
3. **Use version control**: Commit your host config (but not secrets!)
4. **Test incrementally**: Validate after each change
5. **Document custom values**: Create a README in your host directory
6. **Use environment variables for secrets**: Never commit passwords
7. **Keep it organized**: Group related settings together

## Experiment Configurations

Create experiment configs in `experiments/` directory:

```hocon
# experiments/tpch-sf1.yaml
experiment {
    name = "tpch-sf1-baseline"
    runs = 3
    warmup = 1
    dataset = "tpch-sf1"
    queries = [1, 2, 3, 4, 5]
}

# Override system settings for this experiment
tribench {
    systems {
        trino {
            query.max_memory = "2GB"
        }
    }
}
```

## Templates

Templates in `config/templates/` are used to generate system-specific configuration files:

- **Trino Config** (`trino-config.properties.j2`): Generates `config.properties`
- **Trino JVM** (`trino-jvm.config.j2`): Generates `jvm.config`

Templates use Jinja2 syntax and have access to the full configuration tree:

```jinja2
# Template example
coordinator={{ config.tribench.systems.trino.coordinator.enabled|lower }}
http-server.http.port={{ config.tribench.systems.trino.coordinator.port }}
query.max-memory={{ config.tribench.systems.trino.query.max_memory }}
```

## Environment Variables

HOCON supports environment variable substitution:

```hocon
database {
    # Required env var (error if not set)
    password = ${DB_PASSWORD}
    
    # Optional env var (omit key if not set)
    host = ${?DB_HOST}
    
    # Variable substitution in paths
    data_dir = ${HOME}/tribench/data
}
```

## Validation

The configuration system includes validation:

```python
# Validate configuration
errors = loader.validate(config)
if errors:
    for error in errors:
        print(f"Configuration error: {error}")
```

## Best Practices

1. **Never modify `reference.conf` directly** - Create host or experiment overrides
2. **Use environment variables for secrets** - Don't commit passwords
3. **Document custom settings** - Add comments to explain overrides
4. **Test configurations** - Use dry-run mode to verify settings
5. **Version control** - Commit reference and host configs, not generated files

## See Also

- [HOCON Specification](https://github.com/lightbend/config/blob/master/HOCON.md)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- `SECTION_1.2_SUMMARY.md` - Detailed implementation notes


