# TriBench Environment Setup Guide

## Prerequisites

- **Anaconda** or **Miniconda** installed ([Download](https://docs.conda.io/en/latest/miniconda.html))
- **Python 3.11+** (managed by Conda)
- **Docker Desktop** for Mac ([Download](https://www.docker.com/products/docker-desktop))
- **Git** for version control

## Quick Start (Recommended)

### 1. Create Conda Environment

```bash
# Navigate to project directory
cd /Users/adamyuan/Documents/UofG/Yr\ 4/Dissertation/Code/tribench-framework

# Create environment from file
conda env create -f environment.yml

# Activate environment
conda activate tribench

# Verify installation
python -c "import trino, pyhocon, click; print('✅ Core dependencies installed')"
```

### 2. Install TriBench in Development Mode

```bash
# Install package in editable mode
pip install -e .

# Verify CLI works
tribench --version
```

### 3. Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=lib/tribench --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Alternative Setup Methods

### Option A: Using pip + venv (Without Conda)

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### Option B: Using requirements.txt with Conda

```bash
# Create basic conda environment
conda create -n tribench python=3.11

# Activate environment
conda activate tribench

# Install from requirements.txt
pip install -r requirements.txt
pip install -e .
```

## Environment Management

### Update Environment

```bash
# After modifying environment.yml
conda env update -f environment.yml --prune
```

### Export Current Environment

```bash
# Export exact package versions
conda env export > environment-lock.yml

# Export cross-platform compatible
conda env export --from-history > environment-minimal.yml
```

### Remove Environment

```bash
# Deactivate first
conda deactivate

# Remove environment
conda env remove -n tribench
```


```bash
# Check Docker status
docker ps

# If not running, start Docker Desktop from Applications
```

### Issue: Import errors after installation

**Solution**: Ensure you're in the right directory and environment:

```bash
# Check Python path
python -c "import sys; print(sys.executable)"

# Should show: .../envs/tribench/bin/python

# Reinstall package
pip install -e . --force-reinstall --no-deps
```

## Development Workflow

### Daily Workflow

```bash
# 1. Activate environment
conda activate tribench

# 2. Pull latest changes
git pull

# 3. Update environment if needed
conda env update -f environment.yml --prune

# 4. Make changes...

# 5. Run tests
pytest tests/

# 6. Format code
black lib/ tests/

# 7. Lint
flake8 lib/ tests/
```

### IDE Setup (VS Code)

1. **Select Python Interpreter**:
   - `Cmd+Shift+P` → "Python: Select Interpreter"
   - Choose: `Python 3.11.x ('tribench')`

2. **Install Recommended Extensions**:
   - Python (Microsoft)
   - Pylance
   - Python Test Explorer

3. **Configure Settings** (`.vscode/settings.json`):

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.formatting.provider": "black",
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true
}
```

## Next Steps

Once setup is complete:

1. **Read the documentation**: `docs/ARCHITECTURE.md`
2. **Run example experiments**: `examples/01-hello-trino/`
3. **Start development**: Follow `IMPLEMENTATION_PLAN.md`

## Getting Help

- **Framework issues**: Check `docs/FAQ.md`
- **Trino issues**: [Trino Documentation](https://trino.io/docs/current/)
- **Python issues**: [Python 3.11 Docs](https://docs.python.org/3.11/)
```