# Backwards Compatibility Wrapper Removal - Work Estimate

## Summary

Removing all 12 backwards compatibility wrappers and updating imports would require:

- **Files to delete:** 12 wrapper files
- **Files to update:** 23 source files  
- **Import statements to change:** 36 total

**Estimated effort: 3-4 hours total**

---

## Breakdown

### 1. Files to Delete (12 wrapper files)

```
lib/tribench/experiments/trino_experiment.py
lib/tribench/storage/result_storage.py
lib/tribench/utils/config.py
lib/tribench/systems/kubernetes_system.py
lib/tribench/systems/trino.py
lib/tribench/data/dataset.py
lib/tribench/data/iceberg_loader.py
lib/tribench/monitoring/trino_monitor.py
lib/tribench/cli/result_commands.py
lib/tribench/cli/system_commands.py
lib/tribench/cli/data_commands.py
lib/tribench/cli/suite_commands.py
```

### 2. Files Requiring Import Updates (23 files)

```
lib/tribench/analysis/performance.py
lib/tribench/cli/base.py
lib/tribench/cli/config_commands.py
lib/tribench/cli/data/generate_commands.py
lib/tribench/cli/data/load_commands.py
lib/tribench/cli/data/query_commands.py
lib/tribench/cli/data/utils.py
lib/tribench/cli/data/validation_commands.py
lib/tribench/cli/suite/run_commands.py
lib/tribench/cli/suite/utils.py
lib/tribench/cli/system/lifecycle_commands.py
lib/tribench/cli/system/status_commands.py
lib/tribench/cli/system/utils.py
lib/tribench/data/__init__.py
lib/tribench/data/iceberg/loader.py
lib/tribench/systems/__init__.py
lib/tribench/systems/hive_metastore.py
lib/tribench/systems/kubernetes/manifests.py
lib/tribench/systems/minio.py
lib/tribench/systems/postgresql.py
lib/tribench/systems/trino/config_generator.py
lib/tribench/systems/trino/health.py
lib/tribench/systems/trino/system.py
```

### 3. Import Statement Changes (36 total)

| Old Import Pattern | New Import Pattern | Occurrences |
|---|---|---|
| `from tribench.utils.config import` | `from tribench.utils.config import` (unchanged*) | 18 |
| `from tribench.data.dataset import` | `from tribench.data.dataset import` (unchanged*) | 7 |
| `from tribench.systems.trino import TrinoSystem` | `from tribench.systems.trino import TrinoSystem` (unchanged*) | 5 |
| `from tribench.systems.kubernetes_system import` | `from tribench.systems.kubernetes import` | 4 |
| `from tribench.storage.result_storage import` | `from tribench.storage.result import` | 1 |
| `from tribench.data.iceberg_loader import` | `from tribench.data.iceberg import` | 1 |

*Note: Some imports remain unchanged because the package structure already matches (e.g., `utils.config`, `data.dataset`, `systems.trino`)

---

## Detailed Work Breakdown

### Phase 1: Preparation (30 minutes)
- Write automated search & replace script
- Test script on a backup branch
- Review change list for edge cases

### Phase 2: Execute Changes (1.5-2 hours)
- Run automated script for straightforward replacements
- Manually update complex imports (if any)
- Update `__init__.py` files if needed
- Delete wrapper files

### Phase 3: Testing (1 hour)
- Run all CLI commands to verify functionality
- Test import statements in Python REPL
- Run test suite (if available)
- Check for any runtime errors

### Phase 4: Documentation (30 minutes)
- Update REFACTORING_SUMMARY.md
- Add migration notes
- Update any affected documentation

---

## Automation Script Approach

A Python script could automate most of this work:

```python
#!/usr/bin/env python3
"""Remove backwards compatibility wrappers and update imports."""

import re
from pathlib import Path

REPLACEMENTS = [
    (r'from tribench\.systems\.kubernetes_system import', 
     'from tribench.systems.kubernetes import'),
    (r'from tribench\.storage\.result_storage import', 
     'from tribench.storage.result import'),
    (r'from tribench\.data\.iceberg_loader import', 
     'from tribench.data.iceberg import'),
    (r'from tribench\.monitoring\.trino_monitor import', 
     'from tribench.monitoring.trino import'),
    (r'from tribench\.experiments\.trino_experiment import', 
     'from tribench.experiments.trino import'),
]

WRAPPER_FILES = [
    'lib/tribench/experiments/trino_experiment.py',
    'lib/tribench/storage/result_storage.py',
    # ... (all 12 files)
]

def update_imports(file_path):
    """Update imports in a single file."""
    content = file_path.read_text()
    modified = False
    
    for old_pattern, new_import in REPLACEMENTS:
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_import, content)
            modified = True
    
    if modified:
        file_path.write_text(content)
        return True
    return False

def main():
    # Update all imports
    for py_file in Path('lib').rglob('*.py'):
        if py_file.name.endswith('.bak'):
            continue
        if str(py_file) in WRAPPER_FILES:
            continue
        
        if update_imports(py_file):
            print(f"Updated: {py_file}")
    
    # Delete wrapper files
    for wrapper in WRAPPER_FILES:
        Path(wrapper).unlink()
        print(f"Deleted: {wrapper}")

if __name__ == '__main__':
    main()
```

---

## Risk Assessment

### Low Risk
- Most imports are straightforward replacements
- Automated script can handle bulk changes
- Easy to test with CLI commands

### Medium Risk
- Some files have multiple import patterns to update
- Need to ensure all references are updated
- Documentation and examples also need updates

### Mitigation
- Use version control (Git) for easy rollback
- Test thoroughly on a separate branch first
- Keep backup files until fully tested
- Run comprehensive integration tests

---

## Recommendation

**Recommended Approach:** Keep wrappers for now

**Reasons:**
1. **Current setup is working** - All CLI commands function correctly
2. **Zero breaking changes** - Existing code continues to work
3. **Low maintenance cost** - Wrappers are simple import forwarding
4. **Gradual migration** - New code can use new imports while old code works
5. **Documentation value** - Wrappers serve as API documentation

**When to remove wrappers:**
- Major version bump (v2.0)
- After 6-12 month deprecation period
- When releasing breaking changes anyway
- If wrapper maintenance becomes burdensome

**Better alternative:**
Add deprecation warnings to wrappers:

```python
import warnings

warnings.warn(
    "Importing from tribench.experiments.trino_experiment is deprecated. "
    "Use 'from tribench.experiments.trino import TrinoExperiment' instead.",
    DeprecationWarning,
    stacklevel=2
)

from tribench.experiments.trino import TrinoExperiment
```

This allows:
- Gradual migration with clear warnings
- Time for users to update their code
- No breaking changes
- Easy tracking of deprecated import usage

---

## Conclusion

While removing the wrappers is **feasible in 3-4 hours**, the **current approach with backwards compatibility is recommended** for:
- Stability
- User experience  
- Gradual migration path
- Low risk

The refactoring has successfully achieved its goal of improving code organization while maintaining full backwards compatibility. Removing wrappers can be deferred to a future major release.
