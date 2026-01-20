# Config-Based Backend Selection Implementation

## Overview
Implemented configuration-based backend selection to reduce CLI friction while maintaining backward compatibility. Users can now set their preferred backend (Docker or Kubernetes) once in their configuration file instead of specifying `--kind` on every command.

## Motivation
- **Problem**: Repeatedly typing `--kind` flag for Kubernetes deployments was tedious
- **Goal**: Enable personal default (Kubernetes) without breaking Docker support for others
- **Solution**: Config-based backend with explicit flag override

## Changes Made

### 1. Configuration Option (`config/reference.conf`)
Added new backend configuration option:

```hocon
tribench {
  defaults {
    # Default backend for system deployment
    # Valid values: "docker", "kubernetes"
    # Can be overridden per-host or with --kind flag
    backend = "docker"
  }
}
```

**Usage**: Users set `tribench.defaults.backend = "kubernetes"` in their host config file (e.g., `config/hosts/gcp-gke.conf`)

### 2. Backend Resolution Helper (`lib/tribench/cli/base.py`)
Created `should_use_kubernetes(kind, config)` helper function:

```python
def should_use_kubernetes(kind, config):
    """Determine whether to use Kubernetes backend.
    
    Priority:
    1. Explicit --kind flag (if provided)
    2. Configuration backend setting (tribench.defaults.backend)
    3. Default to Docker
    
    Args:
        kind: Boolean from --kind flag
        config: ConfigTree or dict from ConfigurationLoader
        
    Returns:
        bool: True if Kubernetes should be used
    """
```

**Features**:
- Priority system: flag > config > default
- Handles both ConfigTree and dict inputs
- Graceful error handling for missing config keys

### 3. Updated Commands

#### System Lifecycle Commands (`lib/tribench/cli/system/lifecycle_commands.py`)
- Updated: `setup()`, `start()`, `stop()`, `teardown()`
- Pattern: Load config → call helper → branch on result
- Added `@config_option` decorator where missing
- Enhanced verbose output showing backend source

#### Status Command (`lib/tribench/cli/system/status_commands.py`)
- Updated: `status()`
- Added config loading and backend resolution
- Added `@config_option` decorator

#### Data Load Commands (`lib/tribench/cli/data/load_commands.py`)
- Updated: `load()`
- Changed from `if kind:` to `use_k8s = should_use_kubernetes(kind, full_config)`
- Backward compatible with deprecated `load_iceberg()` command

#### Experiment Command (`lib/tribench/cli/experiment_commands.py`)
- Updated: `run()`
- Added config loading and backend resolution

#### Suite Command (`lib/tribench/cli/suite/run_commands.py`)
- Updated: `run_suite()`
- Changed system lifecycle setup logic to use `use_k8s` variable
- Removed redundant config loading (already done for backend resolution)

## Backward Compatibility

✅ **Fully backward compatible**:
- `--kind` flag still works as explicit override
- Default behavior unchanged (Docker)
- No breaking changes to CLI interface
- Config option is optional

## Usage Examples

### Before (always needing --kind)
```bash
tribench sys setup --kind
tribench sys start --kind
tribench data load tpch-tiny --kind
tribench exp run experiments/test.yaml --kind
tribench sys stop --kind
```

### After (with config setting)
```bash
# In config/hosts/my-cluster.conf:
tribench.defaults.backend = "kubernetes"

# Now commands use Kubernetes by default:
tribench sys setup
tribench sys start
tribench data load tpch-tiny
tribench exp run experiments/test.yaml
tribench sys stop

# Can still explicitly use Docker if needed:
# (Note: currently requires --kind=false to be implemented)
```

### Per-Command Override
```bash
# Default is Kubernetes (from config)
tribench sys start

# Explicitly use Docker instead
# (Currently handled by not setting the flag; explicit override TBD)
```

## Implementation Pattern

Standard pattern applied across all commands:

```python
@click.command(name="command")
@kind_option  # Still present for backward compatibility
@config_option
# ... other decorators
def command(ctx, kind, config, ...):
    # Load configuration
    loader = ConfigurationLoader()
    cfg = loader.load(experiment_config=config) if config else loader.load()
    
    # Determine backend
    use_k8s = should_use_kubernetes(kind, cfg)
    
    # Branch logic
    if use_k8s:
        # Kubernetes code path
        if not ensure_k8s_port_forwarding(cfg):
            return
        # ... K8s operations
    else:
        # Docker code path
        auto_ensure_trino_connection(cfg)
        # ... Docker operations
```

## Testing Checklist

- [ ] Test with `backend = "kubernetes"` in config
  - [ ] Verify commands work without `--kind` flag
  - [ ] Verify port forwarding is established
  - [ ] Verify experiments execute correctly
  
- [ ] Test with `backend = "docker"` in config (or default)
  - [ ] Verify Docker Compose path is taken
  - [ ] Verify Trino connection works
  
- [ ] Test explicit `--kind` flag override
  - [ ] With `backend = "docker"` in config, `--kind` should use K8s
  - [ ] With `backend = "kubernetes"` in config, `--kind` should still use K8s
  
- [ ] Test without config setting (default behavior)
  - [ ] Should default to Docker
  - [ ] `--kind` flag should enable K8s

## Future Enhancements

1. **Explicit Docker Override**: Add `--docker` flag or `--kind=false` to explicitly force Docker when K8s is default
2. **Auto-detection**: Detect running K8s cluster and auto-select backend
3. **Per-experiment Backend**: Allow experiments to specify backend in YAML
4. **Validation**: Add config validation to ensure backend value is valid

## Related Files

- `config/reference.conf` - Default configuration with backend option
- `lib/tribench/cli/base.py` - Backend resolution helper
- `lib/tribench/cli/system/lifecycle_commands.py` - System lifecycle commands
- `lib/tribench/cli/system/status_commands.py` - Status command
- `lib/tribench/cli/data/load_commands.py` - Data loading commands
- `lib/tribench/cli/experiment_commands.py` - Experiment execution
- `lib/tribench/cli/suite/run_commands.py` - Suite execution

## Notes

- Implementation maintains dissertation requirement for both Docker (local dev) and Kubernetes (cluster) support
- No Docker Compose code was removed - only routing logic changed
- Config hierarchy maintained: reference.conf → host config → experiment config → env vars
- Backend resolution is fail-safe: defaults to Docker if config is missing or invalid
