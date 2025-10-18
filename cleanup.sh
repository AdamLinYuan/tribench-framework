#!/bin/bash
# TriBench Repository Cleanup Script
# This script removes build artifacts, caches, and runtime files

set -e  # Exit on error

echo "🧹 TriBench Repository Cleanup"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to safely remove files/directories
safe_remove() {
    if [ -e "$1" ]; then
        echo -e "${YELLOW}Removing:${NC} $1"
        rm -rf "$1"
    fi
}

# Function to get directory size
get_size() {
    if [ -e "$1" ]; then
        du -sh "$1" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

echo "📊 Calculating space to be freed..."
TOTAL_SIZE=0

# Calculate sizes
HTMLCOV_SIZE=$(get_size "htmlcov")
PYCACHE_SIZE=$(du -sh $(find . -type d -name __pycache__) 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "0")
DOWNLOADS_SIZE=$(get_size "downloads/trino-server-434.tar.gz")
SYSTEMS_SIZE=$(get_size "systems/trino-434")
LOGS_SIZE=$(get_size "log")

echo ""
echo "Space to be freed:"
echo "  - htmlcov/: $HTMLCOV_SIZE"
echo "  - __pycache__/: ${PYCACHE_SIZE}K"
echo "  - downloads/*.tar.gz: $DOWNLOADS_SIZE"
echo "  - systems/trino-434/: $SYSTEMS_SIZE"
echo "  - log/: $LOGS_SIZE"
echo ""

read -p "Continue with cleanup? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "🔥 Starting cleanup..."
echo ""

# 1. Python build artifacts
echo "1️⃣  Cleaning Python build artifacts..."
safe_remove ".coverage"
safe_remove "coverage.xml"
safe_remove "htmlcov"
safe_remove ".pytest_cache"
safe_remove "lib/tribench.egg-info"
safe_remove "build"
safe_remove "dist"

# 2. Python cache files
echo ""
echo "2️⃣  Cleaning Python cache files..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*~" -delete 2>/dev/null || true

# 3. Downloaded binaries
echo ""
echo "3️⃣  Cleaning downloaded binaries..."
safe_remove "downloads/trino-server-434.tar.gz"
# Keep README
if [ ! -f "downloads/README.md" ]; then
    echo "# Downloads Directory" > downloads/README.md
    echo "" >> downloads/README.md
    echo "System binaries are automatically downloaded here by TriBench." >> downloads/README.md
    echo "These are cached to avoid re-downloading." >> downloads/README.md
fi

# 4. Runtime systems
echo ""
echo "4️⃣  Cleaning runtime system installations..."
safe_remove "systems/trino-434"
# Keep README
if [ ! -f "systems/README.md" ]; then
    echo "# Systems Directory" > systems/README.md
    echo "" >> systems/README.md
    echo "Running system installations are created here." >> systems/README.md
    echo "Use \`tribench sys setup <system>\` to install systems." >> systems/README.md
fi

# 5. Logs
echo ""
echo "5️⃣  Cleaning logs..."
safe_remove "log/trino"
# Keep log directory structure
mkdir -p log
if [ ! -f "log/README.md" ]; then
    echo "# Logs Directory" > log/README.md
    echo "" >> log/README.md
    echo "System logs are stored here during execution." >> log/README.md
fi

# 6. Results (optional - ask user)
echo ""
echo "6️⃣  Cleaning experiment results..."
RESULT_COUNT=$(find results -name "*.json" ! -name "README.md" | wc -l)
if [ $RESULT_COUNT -gt 0 ]; then
    echo "Found $RESULT_COUNT result files."
    read -p "Delete result files? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        find results -name "*.json" ! -name "*example*.json" -delete
        echo -e "${GREEN}✓${NC} Deleted result files (kept examples)"
    else
        echo "Kept result files"
    fi
fi

# 7. Datasets (optional - ask user)
echo ""
echo "7️⃣  Checking datasets..."
if [ -d "datasets/tpch-sf1" ] || [ -d "datasets/tpch-sf10" ]; then
    echo "Found generated datasets."
    read -p "Delete generated datasets? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        safe_remove "datasets/tpch-*"
        find datasets -name "*.csv" -delete 2>/dev/null || true
        find datasets -name "*.parquet" -delete 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Deleted datasets"
    else
        echo "Kept datasets"
    fi
fi

# 8. macOS specific
echo ""
echo "8️⃣  Cleaning macOS files..."
find . -name ".DS_Store" -delete 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo ""
echo "💡 Tips:"
echo "  - Run 'make clean' to remove Python artifacts anytime"
echo "  - Deleted binaries will be re-downloaded when needed"
echo "  - Reinstall systems with 'tribench sys setup <system>'"
echo ""
