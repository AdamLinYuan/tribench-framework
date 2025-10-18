# Datasets Directory

This directory contains benchmark datasets managed by TriBench's data commands. Datasets can be generated on-demand or stored statically for reuse across experiments.

## Overview

TriBench provides a comprehensive dataset management system through the `tribench data` command group. This system handles:

- **Dataset Generation**: Create TPC-H datasets at various scale factors using Docker-based dbgen
- **Dataset Registry**: Track generated datasets with metadata and checksums
- **Dataset Validation**: Verify data integrity and completeness
- **Dataset Loading**: Load datasets into Trino catalogs for experiments
- **Dataset Discovery**: List and inspect available datasets

## Dataset Management Commands

### 1. Generate Datasets

Generate TPC-H benchmark datasets at various scale factors:

```bash
# Generate tiny dataset (SF 0.01) - ~26K rows, ~1MB
tribench data generate tpch-tiny

# Generate SF 1 dataset (1GB) 
tribench data generate tpch-sf1

# Generate with options
tribench data generate tpch-sf1 --format parquet --overwrite

# Preview without executing
tribench data generate tpch-sf10 --dry-run
```

**Supported Datasets:**
- `tpch-tiny` - Scale Factor 0.01 (~1 MB, ideal for testing)
- `tpch-sf1` - Scale Factor 1 (~1 GB, standard benchmark)
- `tpch-sf10` - Scale Factor 10 (~10 GB)
- `tpch-sf100` - Scale Factor 100 (~100 GB)

**Options:**
- `--format [parquet|csv]` - Output format (default: parquet)
- `--output PATH` - Custom output directory
- `--overwrite` - Replace existing dataset
- `--dry-run` - Preview without executing
- `--verbose` - Show detailed progress

**What it does:**
1. Runs TPC-H dbgen tool in Docker container
2. Generates CSV data for 8 TPC-H tables (region, nation, customer, supplier, part, partsupp, orders, lineitem)
3. Converts CSV to Parquet format (if specified)
4. Validates generated data
5. Registers dataset in registry.yaml with metadata

### 2. List Datasets

View all registered datasets with their metadata:

```bash
# List all datasets
tribench data list

# Filter by pattern
tribench data list --filter "tpch-sf*"

# Show only generated datasets
tribench data list --generated-only

# Verbose output
tribench data list --verbose
```

**Output includes:**
- Dataset name and type
- Format (parquet/csv)
- Scale factor
- Number of tables
- Total row count
- Total size
- Location path
- Creation timestamp

### 3. Show Dataset Information

Display detailed information about a specific dataset:

```bash
# Basic information
tribench data info tpch-sf1

# Detailed view with checksums
tribench data info tpch-sf1 --detailed
```

**Shows:**
- Dataset metadata (type, format, scale factor, generator)
- Per-table row counts
- Total size and rows
- Dataset properties
- File checksums (in detailed mode)
- Creation timestamp

### 4. Validate Datasets

Verify dataset integrity and completeness:

```bash
# Basic validation
tribench data validate tpch-sf1

# Validate with checksums
tribench data validate tpch-sf1 --checksums

# Validate row counts
tribench data validate tpch-sf1 --row-counts

# Full validation
tribench data validate tpch-sf1 --checksums --row-counts
```

**Validation checks:**
- File existence and accessibility
- Expected table count
- Row count verification (against TPC-H spec)
- Data integrity via checksums
- Parquet file structure

### 5. Load Datasets into Trino

Load datasets into Trino catalogs for querying:

```bash
# Load into memory catalog (default)
tribench data load tpch-sf1

# Load into specific catalog and schema
tribench data load tpch-sf1 --catalog memory --schema benchmarks

# Load with validation
tribench data load tpch-sf1 --validate

# Preview load commands
tribench data load tpch-sf1 --dry-run
```

**Options:**
- `--system [trino]` - Target system (default: trino)
- `--catalog TEXT` - Trino catalog name (default: memory)
- `--schema TEXT` - Schema/database name (default: tpch)
- `--validate` - Validate data after loading
- `--dry-run` - Show SQL DDL without executing

**What it does:**
1. Connects to Trino server
2. Creates schema if it doesn't exist
3. Generates CREATE TABLE DDL for each table
4. Loads data from Parquet files
5. Optionally validates loaded data

## Directory Structure

After generating datasets, the structure looks like:

```
datasets/
├── registry.yaml          # Dataset metadata registry
├── tpch-sf0_01/          # TPC-H Scale Factor 0.01 (tiny)
│   ├── csv/              # CSV format
│   └── parquet/          # Parquet format
│       ├── region.parquet
│       ├── nation.parquet
│       ├── customer.parquet
│       ├── supplier.parquet
│       ├── part.parquet
│       ├── partsupp.parquet
│       ├── orders.parquet
│       └── lineitem.parquet
├── tpch-sf1/             # TPC-H Scale Factor 1
│   ├── csv/
│   └── parquet/
└── tpch-sf10/            # TPC-H Scale Factor 10
    ├── csv/
    └── parquet/
```

## Dataset Registry

The `registry.yaml` file tracks all generated datasets with metadata:

```yaml
datasets:
  tpch-tiny:
    name: tpch-tiny
    type: generated
    format: parquet
    scale_factor: 0.01
    tables:
      region:
        rows: 5
        path: tpch-sf0_01/parquet/region.parquet
      customer:
        rows: 1500
        path: tpch-sf0_01/parquet/customer.parquet
      # ... more tables
    total_rows: 26599
    total_size_bytes: 1322458
    created_at: "2025-10-17T12:31:52.855937"
    generator: tpch-dbgen
    properties:
      tpch_version: "3.0"
    checksums:
      region: 2e4e3e198c275c07...
      # ... more checksums
```

## TPC-H Tables

Generated TPC-H datasets include 8 tables:

1. **region** (5 rows) - Geographic regions
2. **nation** (25 rows) - Countries within regions
3. **customer** (SF × 150,000 rows) - Customer information
4. **supplier** (SF × 10,000 rows) - Supplier information
5. **part** (SF × 200,000 rows) - Part catalog
6. **partsupp** (SF × 800,000 rows) - Part-supplier relationships
7. **orders** (SF × 1,500,000 rows) - Customer orders
8. **lineitem** (SF × 6,000,000 rows) - Order line items

Where SF = Scale Factor (e.g., 0.01, 1, 10, 100)

## Dataset Formats

### Parquet Format (Recommended)
- Columnar storage optimized for analytics
- Efficient compression
- Predicate pushdown support
- Schema embedded in files
- Fast query performance

### CSV Format
- Human-readable
- Universal compatibility
- Larger file sizes
- Useful for debugging

## Usage in Experiments

Datasets can be used in experiments by:

1. **Using Trino's built-in TPC-H catalog** (no generation needed):
   ```yaml
   connection:
     catalog: "tpch"
     schema: "tiny"  # or sf1, sf10, etc.
   ```

2. **Loading generated datasets** into memory catalog:
   ```bash
   tribench data generate tpch-sf1
   tribench data load tpch-sf1 --catalog memory --schema benchmarks
   ```

3. **Referencing in experiment YAML**:
   ```yaml
   connection:
     catalog: "memory"
     schema: "benchmarks"
   ```

## Adding New Datasets

1. Create directory structure
2. Add dataset manifest file
3. Include validation checksums
4. Document data lineage

Example manifest:
```yaml
# datasets/tpch/sf1/manifest.yaml
name: "TPC-H Scale Factor 1"
description: "Standard TPC-H dataset at 1GB scale"
format: "parquet"
size: "1GB"
tables:
  - name: "customer"
    rows: 150000
    size: "24MB"
  - name: "lineitem"  
    rows: 6001215
    size: "759MB"
checksum: "sha256:abc123..."
generated_by: "TPC-H dbgen v3.0.0"
generated_date: "2024-01-01"
```
