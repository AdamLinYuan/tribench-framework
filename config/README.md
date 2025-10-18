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

Create a host-specific configuration in `config/hosts/<your-hostname>/application.conf`:

```hocon
# Override for development machine
tribench {
    systems {
        trino {
            coordinator.jvm.heap = "4G"  # More RAM on dev machine
        }
    }
    
    # Custom paths
    app.path {
        downloads = "/tmp/tribench/downloads"
        systems = "/tmp/tribench/systems"
    }
}
```

The framework automatically detects your hostname and loads the appropriate config.

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


