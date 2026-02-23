# Datasets Directory

This directory contains benchmark datasets managed by TriBench's data commands. Datasets can be generated on-demand, stored statically for reuse, or added as custom datasets with zero configuration.

## Overview

TriBench provides a comprehensive dataset management system through the `tribench data` command group. This system handles:

- **Dataset Generation**: Create TPC-H datasets at various scale factors using Docker-based dbgen
- **Dataset Registry**: Track generated datasets with metadata and checksums
- **Dataset Validation**: Verify data integrity and completeness
- **Dataset Loading**: Load datasets into Trino catalogs for experiments
- **Dataset Discovery**: List and inspect available datasets
- **Custom Datasets**: Auto-discover and load any Parquet files without registration (NEW)

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

Load datasets into Trino catalogs for querying. Supports both registered datasets (TPC-H) and custom datasets (auto-discovered):

```bash
# Load registered dataset (TPC-H)
tribench data load tpch-sf1

# Load custom dataset (auto-discovery)
tribench data load my-custom-data --catalog iceberg --schema my_schema

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
1. Checks if dataset is registered in registry.yaml
2. If not registered, auto-discovers Parquet files in datasets/<name>/ directory
3. Reads schemas directly from Parquet metadata (no manual definition needed)
4. Connects to Trino server and creates schema if needed
5. Generates CREATE TABLE DDL for each table
6. Loads data using fast CTAS pipeline
7. Optionally validates loaded data

**Custom Dataset Auto-Discovery:**
- Detects any directory in `datasets/` that contains `.parquet` files
- Infers table names from filenames (e.g., `customers.parquet` → `customers` table)
- Auto-extracts schemas from Parquet metadata
- No registration or schema definition required
- Same loading performance as TPC-H datasets

## Custom Datasets (Zero Configuration)

**NEW:** TriBench now supports loading custom datasets without any schema definition or registration. Simply place Parquet files in a directory and load them!

### Quick Start

```bash
# 1. Create directory for your dataset
mkdir datasets/my-dataset

# 2. Add Parquet file(s)
# Example: Convert CSV to Parquet
python -c "
import pandas as pd
df = pd.read_csv('data.csv')
df.to_parquet('datasets/my-dataset/table.parquet')
"

# 3. Load into Trino (auto-discovery!)
tribench data load my-dataset --catalog iceberg --schema my_schema

# That's it! No schema definition, no registration needed.
```

### How It Works

1. **Auto-Discovery**: Framework scans `datasets/<name>/` for `*.parquet` files
2. **Schema Inference**: Reads PyArrow schemas directly from Parquet metadata
3. **Table Mapping**: Filename becomes table name (e.g., `customers.parquet` → `customers`)
4. **Fast Loading**: Uses same UniversalIcebergLoader as TPC-H (CTAS pipeline)

### Example: Titanic Dataset

```bash
# Downloaded Kaggle Titanic dataset, converted to Parquet
datasets/
└── titanic/
    └── titanic.parquet  # 891 rows, 12 columns

# Load it
$ tribench data load titanic --catalog iceberg --schema titanic

Auto-discovering custom dataset: titanic
Discovered 1 tables:
  • titanic        891 rows, 12 columns,   0.04 MB

Loading into iceberg.titanic...
✓ Custom dataset loaded successfully!

# Query immediately
$ tribench exp run experiments/titanic-analysis.yaml
# 30 queries executed successfully in 59s
```

### Example: Multi-Table E-Commerce Dataset

```bash
datasets/
└── ecommerce/
    ├── customers.parquet     # 1,000 rows
    ├── products.parquet      # 500 rows
    ├── orders.parquet        # 5,000 rows
    └── order_items.parquet   # 15,000 rows

$ tribench data load ecommerce --catalog iceberg --schema ecommerce

Auto-discovering custom dataset: ecommerce
Discovered 4 tables:
  • customers         1,000 rows,  6 columns,   0.02 MB
  • order_items      15,000 rows,  6 columns,   0.24 MB
  • orders            5,000 rows,  6 columns,   0.08 MB
  • products            500 rows,  6 columns,   0.02 MB

✓ All tables loaded into iceberg.ecommerce
```

### Supported Data Sources

Any data that can be converted to Parquet works:

**From CSV:**
```python
import pandas as pd
df = pd.read_csv('data.csv')
df.to_parquet('datasets/my-data/table.parquet')
```

**From Database:**
```python
import pandas as pd
import sqlalchemy as sa
engine = sa.create_engine('postgresql://...')
df = pd.read_sql_table('table_name', engine)
df.to_parquet('datasets/my-data/table.parquet')
```

**From Kaggle:**
```bash
# Download CSV from Kaggle
kaggle datasets download -d <dataset>
# Convert to Parquet (see above)
```

**From Cloud Storage:**
```bash
# Download existing Parquet files
aws s3 cp s3://bucket/data.parquet datasets/my-data/
```

### Features

✅ **Zero Configuration** - No schema classes, no registry entries  
✅ **Automatic Schema Detection** - Reads from Parquet metadata  
✅ **Multi-Table Support** - Multiple `.parquet` files = multiple tables  
✅ **Type Inference** - Handles all PyArrow types (int, float, string, date, etc.)  
✅ **NULL Handling** - Preserves nullable columns from source data  
✅ **Fast Loading** - Same CTAS pipeline as TPC-H benchmarks  
✅ **Mixed Types** - Each table can have different columns/types  
✅ **Rich Feedback** - Shows discovered tables with row counts before loading  

### Limitations

⚠️ **Parquet Only** - CSV files must be converted first  
⚠️ **No Partitioning** - Custom datasets load without partition optimization (can be added later)  
⚠️ **Flat Structure** - All `.parquet` files must be in top-level directory (no subdirectories)  

### Documentation

- **Quick Start**: [CUSTOM_DATASET_QUICKSTART.md](../CUSTOM_DATASET_QUICKSTART.md)
- **Comprehensive Guide**: [docs/CUSTOM_DATASETS_GUIDE.md](../docs/CUSTOM_DATASETS_GUIDE.md)
- **Implementation Details**: [docs/journal/11_custom_dataset_auto_discovery_february_2026.md](../docs/journal/11_custom_dataset_auto_discovery_february_2026.md)

## Directory Structure

After generating datasets and adding custom datasets, the structure looks like:

```
datasets/
├── registry.yaml          # Dataset metadata registry (TPC-H only)
│
├── tpch-sf0_01/          # TPC-H Scale Factor 0.01 (tiny) - REGISTERED
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
│
├── tpch-sf1/             # TPC-H Scale Factor 1 - REGISTERED
│   ├── csv/
│   └── parquet/
│
├── titanic/              # Custom dataset - AUTO-DISCOVERED
│   └── titanic.parquet   # Single table with 891 rows
│
├── ecommerce/            # Custom dataset - AUTO-DISCOVERED
│   ├── customers.parquet
│   ├── products.parquet
│   ├── orders.parquet
│   └── order_items.parquet
│
└── my-dataset/           # Your custom dataset - AUTO-DISCOVERED
    └── *.parquet         # Any Parquet files
```

**Registry vs. Auto-Discovery:**
- **Registered Datasets** (TPC-H): Tracked in `registry.yaml`, optimized partitioning, checksums
- **Custom Datasets**: Auto-discovered from directory, no registration needed, zero config

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

Datasets can be used in experiments in multiple ways:

1. **Using Trino's built-in TPC-H catalog** (no generation needed):
   ```yaml
   connection:
     catalog: "tpch"
     schema: "tiny"  # or sf1, sf10, etc.
   ```

2. **Loading generated TPC-H datasets** into memory catalog:
   ```bash
   tribench data generate tpch-sf1
   tribench data load tpch-sf1 --catalog memory --schema benchmarks
   ```

   ```yaml
   connection:
     catalog: "memory"
     schema: "benchmarks"
   ```

3. **Using custom datasets** (NEW - zero configuration):
   ```bash
   # Place Parquet files in datasets/my-dataset/
   tribench data load my-dataset --catalog iceberg --schema my_schema
   ```

   ```yaml
   connection:
     catalog: "iceberg"
     schema: "my_schema"
   
   queries:
     - name: "my-query"
       sql: "SELECT * FROM my_table"
   ```

**Example: Titanic Dataset Experiment**

```bash
# 1. Add dataset
datasets/titanic/titanic.parquet

# 2. Load it
tribench data load titanic --catalog iceberg --schema titanic

# 3. Create experiment YAML
cat > experiments/titanic-analysis.yaml << 'EOF'
name: "titanic-survival-analysis"
connection:
  catalog: "iceberg"
  schema: "titanic"
queries:
  - name: "overall-survival"
    sql: |
      SELECT 
        COUNT(*) as total,
        SUM(Survived) as survived,
        ROUND(100.0 * SUM(Survived) / COUNT(*), 2) as survival_rate
      FROM titanic
EOF

# 4. Run experiment
tribench exp run experiments/titanic-analysis.yaml
```

## Adding New Datasets

### Method 1: Custom Datasets (Recommended - Zero Configuration)

Simply place Parquet files in a directory:

```bash
# 1. Create directory
mkdir datasets/my-dataset

# 2. Add Parquet file(s)
cp /path/to/data/*.parquet datasets/my-dataset/

# 3. Load (auto-discovery)
tribench data load my-dataset --catalog iceberg --schema my_schema
```

**No registration, no schema definition, no configuration files needed!**

### Method 2: Registered Datasets (Advanced - For optimization)

For datasets requiring optimized partitioning, checksums, or version tracking:

1. Generate/prepare dataset files
2. Create entry in `registry.yaml`
3. Add schema class in `lib/tribench/data/dataset/`
4. Include validation checksums
5. Document data lineage

Example manifest in `registry.yaml`:
```yaml
datasets:
  my-benchmark:
    name: my-benchmark
    type: generated
    format: parquet
    scale_factor: 1.0
    location: datasets/my-benchmark/parquet
    tables:
      table1:
        rows: 1000000
        path: my-benchmark/parquet/table1.parquet
    total_rows: 1000000
    total_size_bytes: 52428800
    created_at: "2026-02-15T10:00:00"
    generator: custom-generator
    properties:
      version: "1.0"
    checksums:
      table1: sha256:abc123...
```

**When to use registered datasets:**
- Need partition optimization for large data
- Require strict checksums and validation
- Want version tracking and metadata
- Building a standard benchmark suite

**When to use custom datasets:**
- Ad-hoc analysis and testing
- Prototyping with real data
- One-off benchmarks
- Quick experiments

## Best Practices

### For Quick Testing (Custom Datasets)
✅ Use Parquet format for best performance  
✅ Keep filenames simple (alphanumeric + underscores)  
✅ One table per file for clarity  
✅ Convert CSV → Parquet using Pandas  
✅ Place in `datasets/<descriptive-name>/`  

### For Production Benchmarks (Registered Datasets)
✅ Register in `registry.yaml` with metadata  
✅ Include checksums for validation  
✅ Document data generation process  
✅ Use scale factors for size variations  
✅ Implement partitioning strategies  

## Further Reading

- **Custom Datasets Quick Start**: [CUSTOM_DATASET_QUICKSTART.md](../CUSTOM_DATASET_QUICKSTART.md)
- **Custom Datasets Guide**: [docs/CUSTOM_DATASETS_GUIDE.md](../docs/CUSTOM_DATASETS_GUIDE.md)
- **Implementation Journal**: [docs/journal/11_custom_dataset_auto_discovery_february_2026.md](../docs/journal/11_custom_dataset_auto_discovery_february_2026.md)
