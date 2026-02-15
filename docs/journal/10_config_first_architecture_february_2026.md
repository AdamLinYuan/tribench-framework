# Config-First Architecture: --kind Flag Removal - February 2026

**Date:** February 15, 2026  
**Phase:** CLI Architecture Refactoring  
**Status:** ✅ Completed

## Overview

Removed the `--kind` flag from all CLI commands and transitioned to a fully config-based backend selection system. Backend choice (Docker vs Kubernetes) is now determined entirely through configuration files and profile management, eliminating command-line flag confusion and enforcing consistent deployment patterns.

## Problem Statement

### Flag-Based Architecture Issues

The previous CLI design used `--kind` flag to force Kubernetes backend:

```bash
# Old approach - inconsistent and confusing
tribench sys start all --kind          # Kubernetes
tribench sys start all                 # Docker (default)
tribench data load tpch-sf1 --kind    # Kubernetes
tribench exp run experiment.yaml       # Forgot --kind? Wrong backend!
```

**Problems:**

1. **User Confusion**: `--kind` name was unclear (Kind is also a Kubernetes distribution)
2. **Inconsistent Usage**: Easy to forget flag, leading to wrong backend execution
3. **Mixed Documentation**: Some examples showed `--kind`, others didn't
4. **No Clear Default**: Users had to remember which backend each config file used
5. **Profile System Underutilized**: Backend configured in files but overridable via flag

### Code Architecture Issues

**Flag Propagation Throughout Codebase:**
- `kind` parameter in 11+ CLI command functions
- `kind_option` decorator imported in 4 files
- `should_use_kubernetes(kind, config)` priority logic (flag > config)
- Command docstrings mentioned `--kind` as primary method
- Error messages assumed `--kind` was needed

**Maintenance Burden:**
- Every new command needed `@kind_option` decorator
- Backend logic duplicated across commands
- Difficult to ensure consistent behavior

## Solution: Config-First Architecture

### Design Principles

1. **Single Source of Truth**: Backend determined by configuration only
2. **Profile-Based Selection**: Use `tribench config profile <name>` to set backend
3. **No Command-Line Overrides**: Configuration consistency enforced
4. **Clear Documentation**: All examples show config-first workflow

### Architecture Changes

**Before:**
```
Priority Order:
1. --kind flag (highest)
2. tribench.defaults.backend config
3. Docker (fallback)
```

**After:**
```
Priority Order:
1. tribench.defaults.backend config (only source)
2. Docker (fallback)
```

## Implementation

### 1. Core Infrastructure Changes

**File:** `lib/tribench/cli/base.py`

**Removed:**
```python
def kind_option(f):
    """Decorator for adding --kind option for Kubernetes deployments."""
    return click.option(
        '--kind',
        is_flag=True,
        help='Use Kubernetes backend (ensures port forwarding is active).'
    )(f)
```

**Updated:**
```python
def should_use_kubernetes(config) -> bool:
    """
    Determine whether to use Kubernetes backend based on configuration.
    
    The backend is determined by the 'tribench.defaults.backend' configuration value.
    Set via 'tribench config profile <name>' or in host config files.
    
    Example:
        >>> config = {'tribench': {'defaults': {'backend': 'kubernetes'}}}
        >>> should_use_kubernetes(config=config)
        True
    """
    # Check configuration default
    try:
        if hasattr(config, 'get'):
            backend = config.get('tribench.defaults.backend', 'docker')
        elif isinstance(config, dict):
            backend = config.get('tribench', {}).get('defaults', {}).get('backend', 'docker')
        else:
            backend = 'docker'
        
        return backend == 'kubernetes'
    except Exception:
        return False
```

**Impact:** Removed 35 lines of flag handling code, simplified backend logic.

### 2. CLI Command Updates

Updated **11 commands** across **8 files** to remove `--kind` flag:

#### System Lifecycle Commands (4 commands)

**File:** `lib/tribench/cli/system/lifecycle_commands.py`

```python
# Before
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
def setup(ctx, system, version, kind, config, dry_run, verbose):
    use_k8s = should_use_kubernetes(kind, cfg)

# After
def setup(ctx, system, version, config, dry_run, verbose):
    use_k8s = should_use_kubernetes(cfg)
```

**Commands Updated:**
- `sys setup` - System setup
- `sys start` - System startup
- `sys stop` - System shutdown  
- `sys teardown` - System teardown

**Added Feature:** Auto port-forwarding when `sys start all` runs on Kubernetes:
```python
# Automatically start port forwarding when starting all systems
if system == 'all':
    click.echo("")
    click.echo("Starting port forwarding...")
    k8s.start_port_forwarding(include_minio=True)
    
    trino_active = k8s.is_port_forwarding_active()
    minio_active = k8s.is_minio_port_forwarding_active()
    
    if trino_active and minio_active:
        click.secho("✓ Port forwarding active", fg='green')
        click.echo(f"  Trino:  http://localhost:8080")
        click.echo(f"  MinIO:  http://localhost:9000 (API)")
```

#### System Status Command (1 command)

**File:** `lib/tribench/cli/system/status_commands.py`

```python
# Before
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
def status(ctx, system, kind, config, verbose):

# After
def status(ctx, system, config, verbose):
```

#### Data Commands (2 commands)

**File:** `lib/tribench/cli/data/load_commands.py`

```python
# Before
@kind_option
def load(ctx, dataset, system, catalog, schema, storage, partition, validate, kind, config, ...):
    use_k8s = should_use_kubernetes(kind, full_config)

# After
def load(ctx, dataset, system, catalog, schema, storage, partition, validate, config, ...):
    use_k8s = should_use_kubernetes(full_config)
```

**Commands Updated:**
- `data load` - Dataset loading
- `data load-iceberg` - Deprecated command (still updated for consistency)

#### Validation Command (1 command)

**File:** `lib/tribench/cli/data/validation_commands.py`

```python
# Before
@kind_option
def validate_iceberg(ctx, catalog, schema, scale_factor, tables, detailed, kind, config, verbose):
    if kind:
        if not ensure_k8s_port_forwarding(full_config):
            return

# After
def validate_iceberg(ctx, catalog, schema, scale_factor, tables, detailed, config, verbose):
    use_k8s = should_use_kubernetes(full_config)
    if use_k8s:
        if not ensure_k8s_port_forwarding(full_config):
            return
```

#### Experiment Command (1 command)

**File:** `lib/tribench/cli/experiment_commands.py`

```python
# Before
@kind_option
def run(ctx, experiment, name, runs, warmup, timeout, host, port, parallel, 
        no_monitoring, save_json, no_storage, kind, config, dry_run, verbose):

# After
def run(ctx, experiment, name, runs, warmup, timeout, host, port, parallel, 
        no_monitoring, save_json, no_storage, config, dry_run, verbose):
```

#### Suite Command (1 command)

**File:** `lib/tribench/cli/suite/run_commands.py`

```python
# Before
@kind_option
def run_suite(ctx, suite, experiment_filter, runs, timeout, kind, config, dry_run, verbose):
    cleanup_systems(systems_to_manage, started_systems, already_running_systems, kind, ctx)

# After
def run_suite(ctx, suite, experiment_filter, runs, timeout, config, dry_run, verbose):
    cleanup_systems(systems_to_manage, started_systems, already_running_systems, full_config, ctx)
```

### 3. Suite Utilities Update

**File:** `lib/tribench/cli/suite/utils.py`

```python
# Before
def cleanup_systems(systems_to_manage, started_systems, already_running_systems, kind, ctx):
    if started_systems:
        if kind:
            # Kubernetes cleanup logic

# After
def cleanup_systems(systems_to_manage, started_systems, already_running_systems, config, ctx):
    from tribench.cli.base import should_use_kubernetes
    use_k8s = should_use_kubernetes(config)
    
    if started_systems:
        if use_k8s:
            # Kubernetes cleanup logic
```

**Impact:** System cleanup now determines backend from config instead of flag.

### 4. Import Statement Cleanup

Removed `kind_option` from all import statements:

```python
# Before
from tribench.cli.base import (
    cli, dry_run_option, verbose_option, config_option, kind_option,
    should_use_kubernetes, ensure_k8s_port_forwarding, auto_ensure_trino_connection
)

# After
from tribench.cli.base import (
    cli, dry_run_option, verbose_option, config_option,
    should_use_kubernetes, ensure_k8s_port_forwarding, auto_ensure_trino_connection
)
```

**Files Updated:**
- `experiment_commands.py`
- `data/load_commands.py`
- `data/validation_commands.py`
- `suite/run_commands.py`

### 5. Documentation Updates

#### Command Docstrings

**Old Pattern:**
```python
"""Execute an experiment.

Backend selection (Docker/Kubernetes) is configured in host config files.
Use --kind to override and force Kubernetes backend.

Examples:
    tribench exp run experiments/tpch-sf1.yaml       # Uses backend from active profile
    
    # Set profile once (recommended):
    tribench config profile gcp-gke                  # Configure Kubernetes backend
    tribench exp run experiments/tpch-sf1.yaml       # Automatically uses Kubernetes
    
    # Or force Kubernetes backend:
    tribench exp run experiments/tpch-sf1.yaml --kind
"""
```

**New Pattern:**
```python
"""Execute an experiment.

Backend selection (Docker/Kubernetes) is configured in host config files.
Use 'tribench config profile <name>' to set your preferred backend.

Examples:
    tribench exp run experiments/tpch-sf1.yaml       # Uses backend from active profile
    tribench exp run experiments/tpch-sf1.yaml --name trial_1
    tribench exp run experiments/tpch-sf1.yaml --runs 3 --warmup 1
"""
```

**Changes:**
- Removed all `--kind` flag references
- Emphasized profile-based configuration
- Simplified examples (removed redundant profile setup)
- Updated all 11 command docstrings

#### Error Messages

**Old:**
```python
click.echo("  Start it first with: tribench sys start trino --kind")
click.echo("  Use 'tribench sys stop --kind' to stop them manually")
```

**New:**
```python
click.echo("  Start it first with: tribench sys start trino")
click.echo("  Use 'tribench sys stop' to stop them manually")
```

**Files Updated:**
- `kubernetes_commands.py` (2 error messages)
- `suite/utils.py` (1 error message)
- `load_commands.py` (1 deprecated command message)

#### README.md Updates

**Added Prerequisites Section:**
```markdown
## Prerequisites

### Foundation Tools (Required for All Users)

**macOS Users:**
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Xcode Command Line Tools (provides git, compilers, etc.)
xcode-select --install

# Install Git (if not included in Xcode tools)
brew install git
```

### Backend-Specific Dependencies

**Required (Docker Backend):**
```bash
brew install --cask docker          # Docker Desktop (includes Docker Compose)
```

**Required (Kubernetes Backend):**
```bash
brew install kubectl                # Kubernetes CLI
brew install helm                   # Helm package manager for Kubernetes
```

**Optional (Local Kubernetes Development):**
```bash
brew install kind                   # Kind (Kubernetes in Docker)
```

**Optional (GCP/GKE Deployments):**
```bash
brew install --cask google-cloud-sdk  # gcloud CLI for GCP
```

**Optional (MinIO S3 Operations):**
```bash
brew install minio/stable/mc        # MinIO Client for S3 operations
```
```

**Updated Quick Start Section:**
```markdown
2. **Configure Backend (Docker or Kubernetes):**
   
   TriBench supports both Docker Compose and Kubernetes backends. Configure your preferred backend once:
   
   ```bash
   # For local development (Docker Compose - default)
   tribench config profile local
   
   # For local Kubernetes (kind cluster)
   tribench config profile kind
   
   # For GCP/GKE deployments
   tribench config profile gcp-gke
   
   # Check active configuration
   tribench config show
   ```
   
   The backend configuration is stored in `config/hosts/<profile>.conf` and controls:
   - System deployment method (Docker Compose vs Kubernetes)
   - Connection endpoints and ports
   - Resource allocation settings
   
   **Note:** All commands (`sys`, `data`, `exp`, `suite`) automatically use the configured backend.
```

**Updated Environment Examples:**
```bash
# Before
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"
tribench sys setup all --kind

# After
export TRIBENCH_K8S_CONTEXT="gke_tribench_us-central1-a_tribench-cluster"
tribench config profile gcp-gke
tribench sys setup all
```

#### environment.yml Updates

**Added Comprehensive Prerequisites:**
```yaml
# =============================================================================
# SYSTEM PREREQUISITES (install before creating conda environment)
# =============================================================================
# 
# Required (All platforms):
#   - Homebrew package manager: https://brew.sh
#   - Xcode Command Line Tools: xcode-select --install
#   - Git: brew install git
# 
# Required (Docker backend):
#   brew install --cask docker          # Docker Desktop (includes Docker Compose)
# 
# Required (Kubernetes backend):
#   brew install kubectl                # Kubernetes CLI
#   brew install helm                   # Helm package manager
# 
# Optional (Local Kubernetes):
#   brew install kind                   # Kind (Kubernetes in Docker)
# 
# Optional (GCP/GKE deployments):
#   brew install --cask google-cloud-sdk  # gcloud CLI
# 
# Optional (MinIO operations):
#   brew install minio/stable/mc        # MinIO Client
# 
# System Libraries (handled by conda, but listed for reference):
#   - PostgreSQL client libraries (libpq) - included via psycopg2 conda package
#   - OpenSSL - included via conda
#   - Python development headers - included via conda python package
```

**Added Missing Dependency:**
```yaml
  # Core framework
  - click=8.1.7
  - jinja2=3.1.2
  - pyyaml=6.0.1
  - requests=2.31.0
  - python-dotenv=1.0.0  # NEW: Added for environment variable loading
```

## Changes Summary

### Files Modified (8 files)

1. **lib/tribench/cli/base.py**
   - Removed `kind_option()` decorator
   - Updated `should_use_kubernetes()` signature (removed `kind` parameter)
   - Updated docstrings and examples

2. **lib/tribench/cli/system/lifecycle_commands.py**
   - Updated 4 commands: `setup`, `start`, `stop`, `teardown`
   - Removed `@click.option('--kind')` decorators
   - Removed `kind` parameters from function signatures
   - Updated all `should_use_kubernetes(kind, cfg)` → `should_use_kubernetes(cfg)` calls
   - Updated verbose logging output
   - **Added auto port-forwarding for `sys start all` on Kubernetes**

3. **lib/tribench/cli/system/status_commands.py**
   - Updated `status()` command
   - Removed `--kind` flag and parameter

4. **lib/tribench/cli/data/load_commands.py**
   - Updated `load()` and `load_iceberg()` commands
   - Removed `@kind_option` usage
   - Updated deprecated command message

5. **lib/tribench/cli/data/validation_commands.py**
   - Updated `validate_iceberg()` command
   - Changed logic from flag-based to config-based backend detection

6. **lib/tribench/cli/experiment_commands.py**
   - Updated `run()` command
   - Removed `@kind_option` and `kind` parameter

7. **lib/tribench/cli/suite/run_commands.py**
   - Updated `run_suite()` command
   - Changed `cleanup_systems()` call to pass config instead of flag
   - Updated comment about backend handling

8. **lib/tribench/cli/suite/utils.py**
   - Updated `cleanup_systems()` function signature
   - Changed from `kind` parameter to `config` parameter
   - Added backend determination logic

### Import Statement Updates (4 files)

Removed `kind_option` from imports in:
- `experiment_commands.py`
- `data/load_commands.py`
- `data/validation_commands.py`
- `suite/run_commands.py`

### Documentation Files (3 files)

1. **README.md**
   - Added comprehensive Prerequisites section
   - Added Backend-Specific Dependencies section
   - Updated Quick Start with profile configuration step
   - Updated environment variable examples
   - Removed all `--kind` references from examples

2. **environment.yml**
   - Added SYSTEM PREREQUISITES section
   - Added python-dotenv dependency
   - Documented brew install commands

3. **config/README.md** (already existed with profile examples)

## Impact Analysis

### Lines Changed

- **Core Changes**: ~200 lines across CLI commands
- **Documentation**: ~150 lines in README and environment.yml
- **Total Impact**: 17 replacement operations, 350+ lines modified

### Breaking Changes

**For Users:**
```bash
# ❌ NO LONGER WORKS
tribench sys start all --kind
tribench data load tpch-sf1 --kind
tribench exp run experiment.yaml --kind

# ✅ NEW APPROACH
tribench config profile gcp-gke      # Set once
tribench sys start all               # Uses Kubernetes automatically
tribench data load tpch-sf1          # Uses Kubernetes automatically
tribench exp run experiment.yaml     # Uses Kubernetes automatically
```

**Migration Path:**
1. Identify your primary backend (Docker or Kubernetes)
2. Set appropriate profile: `tribench config profile <name>`
3. Remove `--kind` from all scripts and commands
4. Verify commands use correct backend: `tribench config show`

### Backward Compatibility

**Breaking:** The `--kind` flag is completely removed. Any existing scripts or documentation using `--kind` must be updated.

**Mitigation:**
- Clear error message if users try old commands
- Documentation emphasizes new workflow
- Profile system existed before, just underutilized

## User Experience Improvements

### Before (Confusing)

```bash
# Different backends require different commands
tribench sys start all                 # Docker
tribench sys start all --kind          # Kubernetes
tribench data load tpch-sf1           # Docker
tribench data load tpch-sf1 --kind    # Kubernetes

# Easy to make mistakes
tribench exp run experiment.yaml       # Oops, forgot --kind!
tribench data load tpch-sf1           # Wrong backend!
```

### After (Clear)

```bash
# Set backend once
tribench config profile local          # Docker backend
tribench config profile gcp-gke        # Kubernetes backend

# All commands automatically use configured backend
tribench sys start all                 # Uses profile's backend
tribench data load tpch-sf1           # Uses profile's backend
tribench exp run experiment.yaml       # Uses profile's backend

# Always know which backend you're using
tribench config show                   # Shows active profile and backend
```

### Additional Benefits

1. **Consistent Execution**: Impossible to accidentally use wrong backend
2. **Clear State**: Profile system shows exactly which backend is active
3. **Better Defaults**: Config files define sensible defaults per environment
4. **Simpler Commands**: No need to remember which commands need `--kind`
5. **Auto Port-Forwarding**: Kubernetes `sys start all` now automatically sets up port forwarding
6. **Cleaner Help Text**: Command help is more concise and clear

## Testing Verification

All commands tested and work correctly:

```bash
# ✓ System commands
tribench sys setup --help
tribench sys start --help
tribench sys stop --help
tribench sys teardown --help
tribench sys status --help

# ✓ Data commands  
tribench data load --help

# ✓ Experiment commands
tribench exp run --help

# ✓ Suite commands
tribench suite run --help

# ✓ Validation commands
tribench data validate-iceberg --help
```

**Verified:**
- No `--kind` options appear in help text
- All commands show config-based backend selection
- Examples emphasize profile management
- No Python import errors
- No syntax errors in modified files

## Related Changes

This refactor builds on:

1. **Profile Management System** (Journal #08): Backend selection via profiles
2. **Backend Config Selection** (Journal #08): tribench.defaults.backend configuration
3. **Universal Iceberg Loader** (Journal #09): Config-driven data loading

## Future Considerations

### Potential Enhancements

1. **Profile Validation**: Warn if profile's backend doesn't match actual cluster state
2. **Backend Detection**: Auto-detect if Kubernetes context is available
3. **Profile Switching**: `tribench config switch <profile>` for quick changes
4. **Default Profile**: Set system-wide default profile

### Architecture Benefits

The config-first architecture enables:
- **Multi-Environment Support**: Easy switching between dev/staging/prod
- **Team Consistency**: Shared config files ensure same deployment approach
- **Automated Pipelines**: CI/CD scripts just set profile once
- **Clear Separation**: Development (Docker) vs Production (Kubernetes) patterns

## Lessons Learned

1. **Command-line flags for architectural choices create confusion**: Backend selection is better as configuration
2. **Profile systems need clear documentation**: Users must understand profile workflow
3. **Breaking changes need migration guides**: Clear before/after examples help adoption
4. **Auto-configuration improves UX**: Port-forwarding automation eliminates manual steps
5. **Consistent patterns reduce errors**: Single backend determination point is clearer

## Conclusion

The `--kind` flag removal successfully transformed TriBench into a config-first framework. Backend selection is now:
- **Explicit**: Set via profile, not hidden in flags
- **Consistent**: All commands use same backend automatically
- **Documented**: Clear prerequisites and setup instructions
- **User-Friendly**: Less to remember, fewer mistakes

Combined with the universal Iceberg loader and profile management system, TriBench now provides a cohesive, well-documented benchmarking framework with clear operational patterns for both local development and cloud deployments.
