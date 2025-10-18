# 🧹 Repository Cleanup Guide

## Current Issues

Your repository contains several unnecessary files and folders that should not be version-controlled:

### 📊 Space Analysis

| Category | Items | Estimated Size | Status |
|----------|-------|----------------|--------|
| HTML Coverage Reports | 26+ files in `htmlcov/` | ~2-5 MB | ❌ Delete |
| Python Cache | 62+ `*.pyc` files, 31+ `__pycache__/` dirs | ~10-20 MB | ❌ Delete |
| Downloaded Binaries | `trino-server-434.tar.gz` | **606 MB** | ❌ Delete |
| Runtime Systems | `systems/trino-434/` | ~50-100 MB | ❌ Delete |
| Logs | `log/trino/` | Varies | ❌ Delete |
| Coverage Data | `.coverage`, `coverage.xml` | <1 MB | ❌ Delete |
| Build Artifacts | `.pytest_cache/`, `*.egg-info/` | <10 MB | ❌ Delete |

**Total Estimated Space to Free: ~700+ MB**

---

## 🎯 Quick Cleanup (Recommended)

### Option 1: Automated Cleanup Script

```bash
cd tribench-framework
./cleanup.sh
```

This interactive script will:
1. ✅ Remove all Python build artifacts and cache
2. ✅ Delete downloaded binaries (606MB freed!)
3. ✅ Clean runtime system installations
4. ✅ Remove logs
5. ✅ Ask before deleting results and datasets
6. ✅ Clean macOS `.DS_Store` files

### Option 2: Manual Cleanup

```bash
# Navigate to project
cd tribench-framework

# Delete coverage reports
rm -rf htmlcov/ .coverage coverage.xml

# Delete Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Delete build artifacts
rm -rf .pytest_cache/ lib/tribench.egg-info/ build/ dist/

# Delete downloaded binaries (606MB!)
rm -f downloads/trino-server-434.tar.gz

# Delete runtime installations
rm -rf systems/trino-434/

# Delete logs
rm -rf log/trino/

# Delete macOS files
find . -name ".DS_Store" -delete
```

### Option 3: Use Makefile

Update your `Makefile` with enhanced clean command:

```bash
make clean-all  # Deep clean including downloads and systems
```

---

## 📝 What Was Created

### 1. `.gitignore` File ✅

A comprehensive `.gitignore` has been created to prevent these files from being tracked by Git in the future.

**Key sections:**
- Python artifacts (`__pycache__/`, `*.pyc`, `*.egg-info/`)
- Testing artifacts (`htmlcov/`, `.coverage`, `.pytest_cache/`)
- Downloaded binaries (`downloads/*.tar.gz`)
- Runtime systems (`systems/trino-*/`)
- Logs (`log/`)
- Results (configurable - currently tracked)
- Datasets (large generated files)

### 2. `cleanup.sh` Script ✅

An interactive cleanup script that safely removes unnecessary files with:
- Size calculations before cleanup
- Confirmation prompts
- Safe removal (checks if files exist)
- Colored output for clarity
- Optional deletion of results/datasets

---

## 🗂️ Directory Structure - After Cleanup

```
tribench-framework/
├── .gitignore              ✅ NEW - Prevents tracking build artifacts
├── cleanup.sh              ✅ NEW - Cleanup script
├── .context7/              ✅ Keep - AI context
├── bin/                    ✅ Keep - CLI entry point
├── config/                 ✅ Keep - Configuration files
├── experiments/            ✅ Keep - Experiment definitions
├── lib/                    ✅ Keep - Core framework code
├── tests/                  ✅ Keep - Test suite
├── apps/                   ✅ Keep - Placeholder
├── datagens/               ✅ Keep - Placeholder
├── datasets/               ✅ Keep - Placeholder (with README)
├── downloads/              ✅ Keep - Directory only (with README)
├── log/                    ✅ Keep - Directory only (with README)
├── results/                ✅ Keep - Directory + README
├── systems/                ✅ Keep - Directory only (with README)
├── utils/                  ✅ Keep - Placeholder
├── README.md               ✅ Keep - Documentation
├── GETTING_STARTED.md      ✅ Keep - Documentation
├── IMPLEMENTATION_PLAN.md  ✅ Keep - Documentation
├── Journal.md              ✅ Keep - Development log
├── Makefile                ✅ Keep - Build automation
├── setup.py                ✅ Keep - Package definition
├── requirements.txt        ✅ Keep - Dependencies
├── environment.yml         ✅ Keep - Conda environment
├── pytest.ini              ✅ Keep - Test configuration
└── VERSION                 ✅ Keep - Version file
```

### What Gets Removed (Auto-Generated)
- ❌ `htmlcov/` - Coverage HTML reports
- ❌ `.coverage` - Coverage database
- ❌ `coverage.xml` - Coverage XML report
- ❌ `.pytest_cache/` - Pytest cache
- ❌ `__pycache__/` - Python bytecode cache (everywhere)
- ❌ `*.pyc` - Compiled Python files
- ❌ `lib/tribench.egg-info/` - Package metadata
- ❌ `downloads/trino-server-434.tar.gz` - Large binary (606MB)
- ❌ `systems/trino-434/` - Runtime installation
- ❌ `log/trino/` - Runtime logs
- ❌ `.DS_Store` - macOS metadata

---

## 🔄 Git Workflow After Cleanup

### Step 1: Run Cleanup
```bash
./cleanup.sh
```

### Step 2: Stage Changes
```bash
# Add the new .gitignore
git add .gitignore cleanup.sh

# Check what will be removed from git tracking
git status
```

You should see deleted files like:
- `htmlcov/` (all files)
- `.coverage`
- `coverage.xml`
- etc.

### Step 3: Commit
```bash
git add -A  # Stage all changes including deletions
git commit -m "chore: Clean up repository and add .gitignore

- Remove build artifacts (htmlcov, .coverage, .pytest_cache)
- Remove Python cache files (__pycache__, *.pyc)
- Remove downloaded binaries (606MB trino tarball)
- Remove runtime installations and logs
- Add comprehensive .gitignore
- Add cleanup.sh script for future cleanups"
```

### Step 4: Push (Optional)
```bash
git push origin main  # or your branch name
```

---

## 🛡️ Prevention - Future Best Practices

### 1. Always Use `.gitignore`
The `.gitignore` file now prevents these issues. Don't remove it!

### 2. Regular Cleanup
```bash
# Before committing changes
make clean

# Deep clean occasionally
./cleanup.sh

# Or manually
make clean-all
```

### 3. Check Before Commits
```bash
# Always review what you're committing
git status
git diff --cached

# Use .gitignore patterns
git check-ignore -v <file>  # Check if file should be ignored
```

### 4. Keep Large Files Out
- Downloaded binaries → Auto-download on demand
- Generated datasets → Regenerate when needed
- Runtime installations → Recreate with `tribench sys setup`
- Logs → Runtime only, not for version control

---

## 📋 Makefile Enhancements (Recommended)

Add these targets to your `Makefile`:

```makefile
# Enhanced clean targets
clean-cache:
	@echo "Cleaning Python cache..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -name ".DS_Store" -delete

clean-test:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -f .coverage coverage.xml

clean-build:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf lib/*.egg-info

clean: clean-cache clean-test clean-build
	@echo "✓ Basic cleanup complete"

clean-downloads:
	@echo "Cleaning downloads (large files)..."
	rm -rf downloads/*.tar.gz downloads/*.zip

clean-systems:
	@echo "Cleaning runtime systems..."
	rm -rf systems/trino-*/
	rm -rf systems/postgresql-*/
	rm -rf systems/minio-*/

clean-all: clean clean-downloads clean-systems
	@echo "✓ Deep cleanup complete"
```

---

## ✅ Verification

After cleanup, verify with:

```bash
# Check repository size
du -sh .

# Check git status
git status

# Verify .gitignore is working
git check-ignore -v htmlcov/  # Should show it's ignored

# Check what's tracked
git ls-files
```

---

## 🚨 Important Notes

### DO NOT Delete These:
- ✅ `lib/` - Core framework code
- ✅ `tests/` - Test suite
- ✅ `config/` - Configuration files
- ✅ `experiments/*.yaml` - Experiment definitions
- ✅ Documentation files (README, etc.)
- ✅ `setup.py`, `requirements.txt`, `environment.yml`

### Safe to Delete (Auto-Generated):
- ❌ `htmlcov/`, `.coverage`, `coverage.xml`
- ❌ `__pycache__/`, `*.pyc`
- ❌ `downloads/*.tar.gz`
- ❌ `systems/trino-*/`
- ❌ `log/`
- ❌ `.pytest_cache/`
- ❌ `lib/tribench.egg-info/`

### Optional (User Data):
- ⚠️ `results/*.json` - Your experiment results (keep if needed)
- ⚠️ `datasets/` - Generated datasets (regenerate when needed)

---

## 💡 Quick Reference

```bash
# Daily cleanup
make clean

# Before git commit
./cleanup.sh
git add -A
git commit -m "your message"

# Check repo size
du -sh .

# Verify .gitignore
git status --ignored

# Reinstall after cleanup
tribench sys setup trino
```

---

**Created**: October 17, 2025  
**Purpose**: Clean up 700+ MB of unnecessary files from tribench-framework repository
