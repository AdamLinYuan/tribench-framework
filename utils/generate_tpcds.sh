#!/bin/bash
# TPC-DS Data Generation Script
# Generates TPC-DS benchmark data and converts to Parquet format

set -e

# Configuration
SCALE_FACTOR=${1:-1}
OUTPUT_DIR="datasets/tpcds-sf${SCALE_FACTOR}"
TPCDS_KIT_DIR="utils/tpcds-kit"
PARALLEL_DEGREE=${2:-4}

echo "========================================="
echo "TPC-DS Data Generation"
echo "========================================="
echo "Scale Factor: ${SCALE_FACTOR}"
echo "Output Directory: ${OUTPUT_DIR}"
echo "Parallel Degree: ${PARALLEL_DEGREE}"
echo "========================================="

# Step 1: Clone TPC-DS tools if not present
if [ ! -d "${TPCDS_KIT_DIR}" ]; then
    echo "Cloning TPC-DS tools..."
    git clone https://github.com/databricks/tpcds-kit.git ${TPCDS_KIT_DIR}
fi

# Step 2: Build dsdgen if not built
if [ ! -f "${TPCDS_KIT_DIR}/tools/dsdgen" ]; then
    echo "Building dsdgen..."
    cd ${TPCDS_KIT_DIR}/tools
    make OS=LINUX
    cd ../..
fi

# Step 3: Generate data
echo "Generating TPC-DS data (Scale Factor ${SCALE_FACTOR})..."
mkdir -p ${OUTPUT_DIR}/dat
cd ${TPCDS_KIT_DIR}/tools

# Use parallel generation if scale factor > 1
if [ ${SCALE_FACTOR} -gt 1 ]; then
    echo "Using parallel generation with ${PARALLEL_DEGREE} processes..."
    ./dsdgen -DIR ../../${OUTPUT_DIR}/dat \
        -SCALE ${SCALE_FACTOR} \
        -PARALLEL ${PARALLEL_DEGREE} \
        -CHILD 1 \
        -FORCE &
    
    for i in $(seq 2 ${PARALLEL_DEGREE}); do
        ./dsdgen -DIR ../../${OUTPUT_DIR}/dat \
            -SCALE ${SCALE_FACTOR} \
            -PARALLEL ${PARALLEL_DEGREE} \
            -CHILD ${i} &
    done
    wait
else
    ./dsdgen -DIR ../../${OUTPUT_DIR}/dat \
        -SCALE ${SCALE_FACTOR} \
        -FORCE
fi

cd ../..

echo "Data generation complete!"

# Step 4: Convert to Parquet using DuckDB
echo "Converting to Parquet format..."
mkdir -p ${OUTPUT_DIR}/parquet

# Check if DuckDB is installed
if ! command -v duckdb &> /dev/null; then
    echo "ERROR: DuckDB is required for conversion. Install with:"
    echo "  brew install duckdb  (macOS)"
    echo "  or download from https://duckdb.org/docs/installation/"
    exit 1
fi

# List of TPC-DS tables
TABLES=(
    "call_center"
    "catalog_page"
    "catalog_returns"
    "catalog_sales"
    "customer"
    "customer_address"
    "customer_demographics"
    "date_dim"
    "household_demographics"
    "income_band"
    "inventory"
    "item"
    "promotion"
    "reason"
    "ship_mode"
    "store"
    "store_returns"
    "store_sales"
    "time_dim"
    "warehouse"
    "web_page"
    "web_returns"
    "web_sales"
    "web_site"
)

# Convert each table
for table in "${TABLES[@]}"; do
    echo "Converting ${table}..."
    
    duckdb << EOF
COPY (
    SELECT * FROM read_csv(
        '${OUTPUT_DIR}/dat/${table}.dat',
        delim='|',
        header=false,
        columns=$(python3 -c "from tribench.data.dataset import TPCDSSchema; schema = TPCDSSchema(); cols = schema.get_schema('${table}'); print({col.name: str(col.type) for col in cols})")
    )
) TO '${OUTPUT_DIR}/parquet/${table}.parquet' (FORMAT PARQUET, COMPRESSION 'SNAPPY');
EOF
done

echo "Conversion complete!"

# Step 5: Generate metadata
echo "Generating dataset metadata..."

cat > ${OUTPUT_DIR}/README.md << EOF
# TPC-DS Scale Factor ${SCALE_FACTOR}

Generated on: $(date)
Generator: TPC-DS dsdgen v3.2.0
Format: Parquet (Snappy compression)

## Tables

$(for table in "${TABLES[@]}"; do
    row_count=$(duckdb -c "SELECT COUNT(*) FROM '${OUTPUT_DIR}/parquet/${table}.parquet'" 2>/dev/null || echo "N/A")
    echo "- ${table}: ${row_count} rows"
done)

## Usage

Load into TriBench:

\`\`\`bash
tribench data load tpcds-sf${SCALE_FACTOR} \\
  --catalog iceberg \\
  --schema tpcds \\
  --partition store_sales:ss_sold_date_sk \\
  --partition catalog_sales:cs_sold_date_sk \\
  --partition web_sales:ws_sold_date_sk
\`\`\`

Run benchmark:

\`\`\`bash
tribench exp run experiments/tpcds-sf${SCALE_FACTOR}.yaml
\`\`\`
EOF

echo "========================================="
echo "TPC-DS data generation complete!"
echo "Output: ${OUTPUT_DIR}/parquet/"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Load data: tribench data load tpcds-sf${SCALE_FACTOR}"
echo "2. Run queries: tribench exp run experiments/tpcds-sf${SCALE_FACTOR}.yaml"
