# TriBench Configuration

Configuration system for the TriBench benchmarking framework.

## Quick Start

```bash
# 1. Check your hostname
hostname

# 2. Copy the template
cp templates/host-template.conf hosts/$(hostname).conf

# 3. Edit and uncomment what you need
nano hosts/$(hostname).conf

# 4. Your config is now automatically loaded!
tribench sys status
```

## Configuration Structure

```
config/
├── reference.conf              # Framework defaults (DO NOT EDIT)
├── hosts/                      # Host-specific configs (auto-loaded by hostname)
│   ├── glaroam2-*.conf        # Your machine config
│   └── gcp-gke.conf           # GCP cluster config
├── templates/
│   └── host-template.conf     # Template with all options
└── kubernetes/
    └── kind-config.yaml       # Local Kind cluster config
```

## Configuration Hierarchy

1. **`reference.conf`** - Framework defaults
2. **`hosts/{hostname}.conf`** - Auto-loaded for your machine
3. **Experiment config** - Passed via `--config` flag

Later configs override earlier ones.

## Key Features

### 1. Automatic Host Detection

Config automatically loads based on your hostname:
```bash
hostname  # → glaroam2-155-209.wireless.gla.ac.uk
# Automatically loads: hosts/glaroam2-155-209.wireless.gla.ac.uk.conf
```

### 2. Backend Configuration

Set your default deployment mode:
```hocon
tribench {
  defaults {
    backend = "kubernetes"  # or "docker"
  }
}
```

Now skip the `--kind` flag:
```bash
tribench sys setup       # Uses Kubernetes automatically
tribench sys start       # No --kind needed
tribench data load tpch  # Backend from config
```

### 3. Environment Variables

Override any value:
```hocon
tribench {
  systems {
    trino {
      coordinator {
        host = "localhost"
        host = ${?TRINO_HOST}  # Override with $TRINO_HOST
      }
    }
  }
}
```

## Common Configurations

### GCP/GKE Cluster

```hocon
tribench {
  defaults {
    backend = "kubernetes"
  }
  
  kubernetes {
    context = "gke_project_zone_cluster"
    namespace = "tribench"
  }
  
  systems {
    hive_metastore {
      kubernetes {
        image = "us-central1-docker.pkg.dev/project/repo/hive:"${tribench.systems.hive_metastore.version}
        imagePullPolicy = "IfNotPresent"
      }
    }
  }
}
```

### Local Development

```hocon
tribench {
  defaults {
    backend = "docker"
    ports {
      trino = 9090  # Custom port
    }
  }
  
  systems {
    trino {
      coordinator {
        jvm {
          heap = "4G"  # More memory
        }
      }
    }
  }
}
```

### Custom Credentials

```hocon
tribench {
  systems {
    minio {
      access_key = "my-key"
      secret_key = "my-secret"
    }
  }
}
```

## Available Options

See **`templates/host-template.conf`** for:
- All configurable options
- Detailed comments
- Example configurations
- Environment variable overrides

See **`reference.conf`** for:
- Current default values
- Complete option reference
- System configurations

## Troubleshooting

### Config not loading?

```bash
# Check hostname matches filename
hostname
ls -la config/hosts/

# Verify config syntax
tribench config show
```

### Override not working?

1. Check the config path (e.g., `tribench.systems.trino.coordinator.host`)
2. Verify HOCON syntax
3. Use `tribench config show` to see merged result

### Backend not defaulting?

```bash
# Check backend setting
grep -A 2 "defaults" config/hosts/$(hostname).conf
tribench config show | grep backend
```

## Documentation

- **Host Template**: `templates/host-template.conf` - Full options with examples
- **Reference Config**: `reference.conf` - Framework defaults
- **Configuration Guide**: `/docs/CONFIGURATION.md` - Detailed documentation
- **Backend Selection**: `/docs/BACKEND_CONFIG_IMPLEMENTATION.md` - New feature docs

## Tips

1. **Minimal overrides** - Only change what you need
2. **Use env vars** for secrets (`${?VAR}` syntax)
3. **Test first** with `tribench config show`
4. **Comment why** you're overriding values
5. **Version control** your host configs (except secrets)


