# Profile Management System Implementation

**Date**: January 20, 2026  
**Objective**: Implement persistent configuration profile management to solve hostname-based config issues

---

## Problem Statement

### Original Issue
The framework used hostname-based configuration detection (`platform.node()`), which caused problems:

1. **Network-dependent hostnames**: Hostname changes when switching networks
   - On university WiFi: `glaroam2-155-209.wireless.gla.ac.uk`
   - On home network: `Mac.mynet`
   - On mobile hotspot: Different hostname entirely

2. **Manual workarounds required**: Users had to:
   - Create multiple config files for the same machine
   - Use `--config` flag on every command
   - Remember which config to use for which network

3. **Poor user experience**: Configuration should be set once and persist

### Real-World Example
```bash
# At university - works fine
tribench sys status
# Using: config/hosts/glaroam2-155-209.wireless.gla.ac.uk.conf

# At home - breaks!
tribench sys status
# Tries to use: config/hosts/Mac.mynet.conf
# Error: Config not found or wrong cluster settings
```

---

## Solution: Persistent Profile System

### Design Principles

1. **Set once, use everywhere**: Profile persists across sessions and networks
2. **Explicit over implicit**: User chooses which config to use
3. **Backward compatible**: Still supports hostname detection as fallback
4. **Simple CLI**: Easy to set, show, and clear profiles

### Implementation

#### 1. Profile Storage
- **File**: `.tribench-profile` in framework root
- **Content**: Single line with profile name (without `.conf` extension)
- **Git**: Already ignored by `.tribench-*` pattern in `.gitignore`

#### 2. Configuration Priority
Updated `ConfigurationLoader._load_host_config()` to check in order:
1. **Active profile** (from `.tribench-profile`) - HIGHEST PRIORITY
2. **Explicit hostname** (if passed as parameter)
3. **Auto-detected hostname** (fallback to `platform.node()`)

#### 3. CLI Commands
Added `tribench config profile` command group with 4 actions:

```bash
tribench config profile show    # Display current profile
tribench config profile set     # Set active profile
tribench config profile clear   # Clear profile (revert to hostname)
tribench config profile list    # List available profiles
```

---

## Code Changes

### Files Modified

#### 1. `lib/tribench/utils/config/loader.py`

**Added profile file path:**
```python
self.profile_file = self.root_path / ".tribench-profile"
```

**Added profile management methods:**
- `get_active_profile()` - Read active profile from file
- `set_active_profile(profile_name)` - Save profile selection
- `clear_active_profile()` - Delete profile file

**Updated `_load_host_config()` with priority system:**
```python
def _load_host_config(self, host_name: Optional[str] = None) -> Optional[ConfigTree]:
    # Priority 1: Check for active profile
    if host_name is None:
        active_profile = self.get_active_profile()
        if active_profile:
            host_name = active_profile
            logger.info(f"Using active profile: {host_name}")
    
    # Priority 2/3: Use provided host_name or auto-detect hostname
    if host_name is None:
        host_name = platform.node()
        logger.debug(f"Auto-detected hostname: {host_name}")
    
    # Load config file...
```

#### 2. `lib/tribench/cli/config_commands.py`

**Added `manage_profile()` command:**
```python
@config_group.command(name="profile")
@click.argument('action', type=click.Choice(['show', 'set', 'clear', 'list']))
@click.argument('profile_name', required=False)
def manage_profile(action: str, profile_name: Optional[str]):
    # Implementation for 4 profile actions
```

**Features:**
- Validates profile exists before setting
- Shows active marker in list output
- Friendly error messages with suggestions
- Shows current hostname when no profile active

---

## Usage Examples

### Initial Setup (GCP GKE Cluster)

```bash
# 1. List available profiles
$ tribench config profile list
Available profiles:
  - Mac.mynet
  - gcp-gke
  - glaroam2-155-209.wireless.gla.ac.uk

# 2. Set GCP profile
$ tribench config profile set gcp-gke
✓ Active profile set to: gcp-gke

# 3. Verify it's active
$ tribench config profile show
Active profile: gcp-gke
Config file: /path/to/config/hosts/gcp-gke.conf

# 4. Now all commands use this profile automatically
$ tribench sys status
Kubernetes System Status:
  Running: True
  Pods:
    - hive-metastore: Running (Ready: True)
    - minio: Running (Ready: True)
    ...
```

### Switching Profiles

```bash
# Switch to local development
$ tribench config profile set local-dev
✓ Active profile set to: local-dev

# Clear profile (revert to hostname detection)
$ tribench config profile clear
✓ Active profile cleared
Will now use hostname detection: Mac.mynet
```

### Profile Persistence

```bash
# Day 1: At university
$ tribench config profile set gcp-gke
$ tribench exp run experiments/tpch-gcp.yaml
# ✓ Works - uses GKE cluster

# Day 2: At home (different network/hostname)
$ tribench exp run experiments/tpch-gcp.yaml
# ✓ Still works - same GKE cluster
# Profile persists across sessions and networks!
```

---

## Benefits Achieved

### 1. Network Independence
- ✅ Profile persists regardless of hostname changes
- ✅ No need to create duplicate config files
- ✅ Consistent behavior across all networks

### 2. Improved User Experience
- ✅ Set once, works everywhere
- ✅ No `--config` flag needed on every command
- ✅ Clear commands to manage configuration

### 3. Multi-Environment Workflow
```bash
# Easy switching between local and cloud
tribench config profile set local-kind     # Local development
tribench config profile set gcp-gke        # Cloud testing
tribench config profile set azure-aks      # Production
```

### 4. Team Collaboration
- Each developer can have their own profile
- Profile file is gitignored (user-specific)
- Config files are shared in repository
- No conflicts when working on different environments

---

## Technical Details

### Profile File Format
```
# .tribench-profile
gcp-gke
```
- Single line, no extension
- Matches filename in `config/hosts/`
- Simple plain text for easy debugging

### Error Handling

**Profile doesn't exist:**
```bash
$ tribench config profile set nonexistent
✗ Failed to set profile: nonexistent

Available profiles:
  - gcp-gke
  - local-dev
  - Mac.mynet
```

**No active profile:**
```bash
$ tribench config profile show
No active profile (using hostname detection)
Current hostname: Mac.mynet
```

### Backward Compatibility

**Old behavior (still works):**
```bash
# Hostname detection (when no profile set)
tribench sys status
# Uses: config/hosts/$(hostname).conf

# Explicit config flag (overrides everything)
tribench sys status --config config/hosts/custom.conf
```

**New behavior (recommended):**
```bash
# Set profile once
tribench config profile set gcp-gke

# All commands use it
tribench sys status
tribench data load tpch-tiny
tribench exp run experiments/tpch-gcp.yaml
```

---

## Related Issues Fixed

### Issue 1: MinIO Bucket Creation
While implementing profiles, discovered that MinIO `warehouse` bucket wasn't created in Kubernetes deployments.

**Root cause:** `kubectl.ensure_bucket()` was called during `start()` but failed silently

**Fix:** Manual bucket creation
```bash
kubectl -n tribench exec deployment/minio -- \
  sh -c "mkdir -p /data/warehouse && chmod 777 /data/warehouse"
```

**TODO:** Investigate why `ensure_bucket()` failed during initial deployment

### Issue 2: Variable Substitution in Host Configs
Config files using `${tribench.systems.hive_metastore.version}` failed to parse.

**Root cause:** HOCON variable substitution doesn't work across config file boundaries

**Fix:** Hardcode version in host configs
```hocon
# Before (broken):
image = "registry/hive-metastore:"${tribench.systems.hive_metastore.version}

# After (working):
image = "registry/hive-metastore:4.0.0"
```

---

## Future Enhancements

### 1. Profile Validation
Add `tribench config profile validate <profile>` to check:
- Config file syntax is valid
- Referenced resources exist (K8s contexts, Docker networks)
- Required credentials are set

### 2. Profile Templates
```bash
tribench config profile create my-gke --from-template gcp-gke
# Creates new profile from template
```

### 3. Environment-Specific Profiles
```bash
tribench config profile set dev    # Development
tribench config profile set staging
tribench config profile set prod
```

### 4. Profile Switching with Confirmation
```bash
tribench config profile set prod
Warning: Switching to production cluster!
Continue? [y/N]:
```

---

## Testing Performed

### Test 1: Profile Persistence
```bash
# Set profile
$ tribench config profile set gcp-gke
✓ Active profile set to: gcp-gke

# Verify file created
$ cat .tribench-profile
gcp-gke

# Restart terminal, verify persistence
$ tribench config profile show
Active profile: gcp-gke
```
**Result:** ✅ PASS

### Test 2: Network Independence
```bash
# At university (WiFi)
$ hostname
glaroam2-155-209.wireless.gla.ac.uk

$ tribench sys status
# ✓ Uses gcp-gke profile (not hostname)

# At home (different network)
$ hostname
Mac.mynet

$ tribench sys status
# ✓ Still uses gcp-gke profile
```
**Result:** ✅ PASS

### Test 3: Profile Switching
```bash
$ tribench config profile set gcp-gke
$ tribench sys status
# Shows Kubernetes pods

$ tribench config profile clear
$ tribench sys status
# Uses hostname config
```
**Result:** ✅ PASS

### Test 4: Error Handling
```bash
$ tribench config profile set nonexistent
✗ Failed to set profile: nonexistent

Available profiles:
  - gcp-gke
  - Mac.mynet
```
**Result:** ✅ PASS

---

## Documentation Updates Needed

### User Guide
- [ ] Add "Configuration Profiles" section to main README
- [ ] Update "Getting Started" to recommend profile setup
- [ ] Add examples for multi-environment workflows

### Config README
- [x] Already has host config documentation
- [ ] Add profile management section
- [ ] Add troubleshooting for common profile issues

### Command Reference
- [ ] Add `tribench config profile` to command documentation
- [ ] Add examples for each profile command

---

## Summary

Successfully implemented a persistent configuration profile system that solves the hostname-based configuration problem. Users can now:

1. **Set a profile once**: `tribench config profile set gcp-gke`
2. **Use it everywhere**: All commands automatically use the active profile
3. **Switch easily**: Change profiles with a single command
4. **Network independence**: Profile persists across different networks

This significantly improves the user experience, especially for users who:
- Work from multiple locations (university, home, coffee shops)
- Have laptops that change hostnames on different networks
- Manage multiple deployment environments (local, GCP, Azure, on-prem)

**Status**: ✅ Fully implemented and tested  
**Next Steps**: Update documentation and consider validation enhancements
