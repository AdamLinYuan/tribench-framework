# Creating and Loading Custom Datasets in TriBench

This guide shows you how to create custom datasets and load them into the TriBench framework for benchmarking.

## Overview

There are **two main approaches**:

1. **Quick & Simple**: Use Parquet files directly (recommended for most users)
2. **Advanced**: Create a custom schema class (for new benchmark types)

---

## Approach 1: Quick Custom Dataset (Parquet Files)

### Step 1: Prepare Your Data as Parquet Files

Create Parquet files for your tables. You can use any tool (Pandas, Spark, DuckDB, etc.):

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Example: Create a custom orders table
orders_data = {
    'order_id': [1, 2, 3],
    'customer_id': [101, 102, 103],
    'order_date': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
    'total_amount': [99.99, 149.50, 75.25]
}

df = pd.DataFrame(orders_data)

# Define schema explicitly for better control
schema = pa.schema([
    ('order_id', pa.int64()),
    ('customer_id', pa.int64()),
    ('order_date', pa.date32()),
    ('total_amount', pa.float64())
])

# Write to Parquet
table = pa.Table.from_pandas(df, schema=schema)
pq.write_table(table, 'datasets/my_dataset/orders.parquet')
```

### Step 2: Organize Your Dataset

Create a directory structure:

```
datasets/
└── my_custom_dataset/
    ├── orders.parquet
    ├── customers.parquet
    ├── products.parquet
    └── README.md  # Optional: document your dataset
```

### Step 3: Load into Iceberg via Python API

```python
from pathlib import Path
from tribench.data.iceberg import UniversalIcebergLoader
from tribench.config import ConnectionConfig
import pyarrow as pa

# Define connection
config = ConnectionConfig(
    host='localhost',
    port=8080,
    user='tribench',
    catalog='iceberg',
    schema='default'
)

# Create loader
loader = UniversalIcebergLoader(config)

# Define your custom schema
class CustomDatasetSchema:
    """Define your dataset structure."""
    
    def get_tables(self):
        return ['orders', 'customers', 'products']
    
    def get_schema(self, table_name):
        schemas = {
            'orders': pa.schema([
                ('order_id', pa.int64()),
                ('customer_id', pa.int64()),
                ('order_date', pa.date32()),
                ('total_amount', pa.float64())
            ]),
            'customers': pa.schema([
                ('customer_id', pa.int64()),
                ('name', pa.string()),
                ('email', pa.string()),
                ('signup_date', pa.date32())
            ]),
            'products': pa.schema([
                ('product_id', pa.int64()),
                ('name', pa.string()),
                ('price', pa.float64()),
                ('category', pa.string())
            ])
        }
        return schemas[table_name]

# Load your dataset
dataset_schema = CustomDatasetSchema()
dataset_path = Path('datasets/my_custom_dataset')

# Load tables one by one
conn = loader._get_connection('iceberg', 'my_schema')
cursor = conn.cursor()
loader._create_schema(cursor, 'my_schema')

for table_name in dataset_schema.get_tables():
    parquet_file = dataset_path / f"{table_name}.parquet"
    table_schema = dataset_schema.get_schema(table_name)
    
    # Create table
    loader._create_iceberg_table(
        cursor, 
        table_name, 
        table_schema
    )
    
    # Load data
    row_count = loader._load_data_fast(
        cursor,
        table_name,
        parquet_file,
        table_schema
    )
    
    print(f"Loaded {table_name}: {row_count:,} rows")

cursor.close()
conn.close()
```

### Step 4: Create Experiment Configuration

```yaml
# experiments/my_custom_benchmark.yaml

name: "my-custom-benchmark"
description: "Custom dataset benchmark"

system: "trino"

connection:
  host: "localhost"
  port: 8080
  user: "tribench"
  catalog: "iceberg"
  schema: "my_schema"  # Your custom schema

runs: 3
warmup_runs: 1
timeout_seconds: 300

# Your custom queries
query_files:
  - "queries/custom_q1.sql"
  - "queries/custom_q2.sql"

# Or inline queries
queries:
  - name: "total_sales"
    sql: |
      SELECT 
        DATE_TRUNC('month', order_date) AS month,
        SUM(total_amount) AS total_sales
      FROM orders
      GROUP BY 1
      ORDER BY 1

  - name: "top_customers"
    sql: |
      SELECT 
        c.name,
        COUNT(o.order_id) AS order_count,
        SUM(o.total_amount) AS total_spent
      FROM customers c
      JOIN orders o ON c.customer_id = o.customer_id
      GROUP BY c.name
      ORDER BY total_spent DESC
      LIMIT 10

result_storage:
  enable_database: true
  enable_json: true
```

### Step 5: Run Your Benchmark

```bash
tribench exp run experiments/my_custom_benchmark.yaml
```

---

## Approach 2: Advanced Custom Schema (New Benchmark Type)

For creating a complete new benchmark type (like TPC-DS, SSB, etc.).

### Step 1: Create Custom Schema Class

```python
# lib/tribench/data/custom_benchmark.py

from tribench.data.dataset import DatasetSchema, BenchmarkType
from enum import Enum
import pyarrow as pa

# Extend BenchmarkType enum
class ExtendedBenchmarkType(Enum):
    TPCH = "tpch"
    TPCDS = "tpcds"
    MY_BENCHMARK = "my_benchmark"  # Add yours


class MyBenchmarkSchema(DatasetSchema):
    """Custom benchmark schema definition."""
    
    def get_benchmark_type(self) -> BenchmarkType:
        return ExtendedBenchmarkType.MY_BENCHMARK
    
    def get_tables(self):
        """Return list of table names."""
        return [
            'orders',
            'customers', 
            'products',
            'order_items'
        ]
    
    def get_schema(self, table_name: str) -> pa.Schema:
        """Define PyArrow schema for each table."""
        schemas = {
            'orders': pa.schema([
                ('order_id', pa.int64()),
                ('customer_id', pa.int64()),
                ('order_date', pa.date32()),
                ('status', pa.string()),
                ('total_amount', pa.decimal128(10, 2))
            ]),
            
            'customers': pa.schema([
                ('customer_id', pa.int64()),
                ('name', pa.string()),
                ('email', pa.string()),
                ('country', pa.string()),
                ('signup_date', pa.date32())
            ]),
            
            'products': pa.schema([
                ('product_id', pa.int64()),
                ('name', pa.string()),
                ('category', pa.string()),
                ('price', pa.decimal128(10, 2)),
                ('stock_qty', pa.int32())
            ]),
            
            'order_items': pa.schema([
                ('order_item_id', pa.int64()),
                ('order_id', pa.int64()),
                ('product_id', pa.int64()),
                ('quantity', pa.int32()),
                ('unit_price', pa.decimal128(10, 2))
            ])
        }
        
        if table_name not in schemas:
            raise KeyError(f"Unknown table: {table_name}")
        
        return schemas[table_name]
```

### Step 2: Generate Your Dataset

```python
# scripts/generate_my_dataset.py

from pathlib import Path
from custom_benchmark import MyBenchmarkSchema
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

def generate_dataset(output_dir: Path, scale_factor: int = 1):
    """
    Generate custom benchmark dataset.
    
    Args:
        output_dir: Directory to write Parquet files
        scale_factor: Multiplier for data size (1 = small, 10 = medium, etc.)
    """
    schema = MyBenchmarkSchema()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate customers
    num_customers = 10000 * scale_factor
    customers = pd.DataFrame({
        'customer_id': range(1, num_customers + 1),
        'name': [f'Customer {i}' for i in range(1, num_customers + 1)],
        'email': [f'customer{i}@example.com' for i in range(1, num_customers + 1)],
        'country': np.random.choice(['US', 'UK', 'CA', 'AU', 'DE'], num_customers),
        'signup_date': pd.date_range('2020-01-01', periods=num_customers, freq='1H')
    })
    
    # Generate products  
    num_products = 1000 * scale_factor
    products = pd.DataFrame({
        'product_id': range(1, num_products + 1),
        'name': [f'Product {i}' for i in range(1, num_products + 1)],
        'category': np.random.choice(['Electronics', 'Clothing', 'Books', 'Home'], num_products),
        'price': np.round(np.random.uniform(5, 500, num_products), 2),
        'stock_qty': np.random.randint(0, 1000, num_products)
    })
    
    # Generate orders
    num_orders = 50000 * scale_factor
    orders = pd.DataFrame({
        'order_id': range(1, num_orders + 1),
        'customer_id': np.random.randint(1, num_customers + 1, num_orders),
        'order_date': pd.date_range('2023-01-01', periods=num_orders, freq='10min'),
        'status': np.random.choice(['pending', 'shipped', 'delivered'], num_orders),
        'total_amount': np.round(np.random.uniform(10, 1000, num_orders), 2)
    })
    
    # Generate order items
    num_items = 150000 * scale_factor
    order_items = pd.DataFrame({
        'order_item_id': range(1, num_items + 1),
        'order_id': np.random.randint(1, num_orders + 1, num_items),
        'product_id': np.random.randint(1, num_products + 1, num_items),
        'quantity': np.random.randint(1, 10, num_items),
        'unit_price': np.round(np.random.uniform(5, 500, num_items), 2)
    })
    
    # Write to Parquet with proper schemas
    for table_name, df in [
        ('customers', customers),
        ('products', products),
        ('orders', orders),
        ('order_items', order_items)
    ]:
        table_schema = schema.get_schema(table_name)
        table = pa.Table.from_pandas(df, schema=table_schema)
        output_file = output_dir / f"{table_name}.parquet"
        pq.write_table(table, output_file)
        print(f"Generated {table_name}: {len(df):,} rows")

if __name__ == '__main__':
    output_dir = Path('datasets/my_benchmark_sf1')
    generate_dataset(output_dir, scale_factor=1)
```

### Step 3: Load Using the Framework

```python
from pathlib import Path
from tribench.data.iceberg import UniversalIcebergLoader
from custom_benchmark import MyBenchmarkSchema

# Initialize
loader = UniversalIcebergLoader()
schema = MyBenchmarkSchema()
dataset_path = Path('datasets/my_benchmark_sf1')

# Load dataset
row_counts = loader.load_dataset(
    dataset_path=dataset_path,
    dataset_schema=schema,
    catalog='iceberg',
    schema='my_benchmark',
    storage_location='s3://warehouse/my_benchmark/',  # Optional
    partition_specs={
        'orders': ['order_date'],  # Partition large tables
        'order_items': ['order_id']
    }
)

print("Loaded tables:", row_counts)
```

---

## Use Case Examples

### Example 1: E-Commerce Benchmark

```python
# Generate e-commerce dataset with realistic patterns
def generate_ecommerce_dataset():
    # Generate realistic order patterns (weekday peak, seasonal trends)
    # Add customer segments (new, regular, premium)
    # Product categories with different price distributions
    # Returns/refunds/cancelled orders
    pass
```

### Example 2: IoT Sensor Benchmark

```python
# Time-series sensor data
sensors_schema = pa.schema([
    ('sensor_id', pa.int64()),
    ('timestamp', pa.timestamp('us')),
    ('temperature', pa.float32()),
    ('humidity', pa.float32()),
    ('location', pa.string())
])

# Partition by date for time-range queries
partition_specs = {
    'sensor_readings': ['timestamp']  # Iceberg will handle date partitioning
}
```

### Example 3: Migration from Existing Database

```python
# Export from PostgreSQL/MySQL to Parquet
import sqlalchemy as sa

engine = sa.create_engine('postgresql://user:pass@localhost/mydb')

tables = ['users', 'transactions', 'products']
for table in tables:
    df = pd.read_sql_table(table, engine)
    df.to_parquet(f'datasets/migrated/{table}.parquet')
```

---

## Best Practices

### 1. Schema Design

```python
# ✅ Good: Explicit types, nullable where appropriate
good_schema = pa.schema([
    ('id', pa.int64(), False),  # NOT NULL
    ('name', pa.string(), False),
    ('email', pa.string(), True),  # Nullable
    ('created_at', pa.timestamp('us'), False)
])

# ❌ Avoid: Using string for everything
bad_schema = pa.schema([
    ('id', pa.string()),
    ('created_at', pa.string())  # Should be timestamp
])
```

### 2. Data Volume Guidelines

| Scale Factor | Rows | Use Case |
|--------------|------|----------|
| 0.01 (tiny) | ~100K | Development, unit tests |
| 1 | ~10M | Local testing, smoke tests |
| 10 | ~100M | Realistic benchmarking |
| 100+ | 1B+ | Production-scale testing |

### 3. Partitioning Strategy

```python
# Partition by frequently filtered columns
partition_specs = {
    # Time-based partitioning (most common)
    'orders': ['order_date'],
    
    # Multi-column partitioning
    'events': ['event_date', 'region'],
    
    # Don't partition small tables (<1M rows)
    # 'countries': []  # Skip partitioning
}
```

### 4. Data Quality

```python
# Add data validation before loading
def validate_parquet_file(filepath):
    table = pq.read_table(filepath)
    
    # Check for nulls in required columns
    schema = table.schema
    for i, field in enumerate(schema):
        if not field.nullable:
            null_count = table.column(i).null_count
            assert null_count == 0, f"Found {null_count} nulls in {field.name}"
    
    # Check data ranges
    # Check referential integrity
    # etc.
```

---

## Troubleshooting

### Issue: "Table already exists"

```python
# Solution: Drop before loading
cursor.execute("DROP TABLE IF EXISTS my_table")
```

### Issue: "Schema mismatch"

```python
# Solution: Verify PyArrow schema matches Parquet file
table = pq.read_table('myfile.parquet')
print(table.schema)  # Compare with your defined schema
```

### Issue: "Out of memory during load"

```python
# Solution: Adjust batch size in _load_data_fast
# Or load tables sequentially, not all at once
```

---

## Summary

**For most users**: Use Approach 1 (Parquet files)
- Faster to get started
- Works with any data source
- Flexible and simple

**For framework contributors**: Use Approach 2 (Custom Schema)
- Adds new benchmark type to framework
- Reusable and well-structured
- Can be integrated into CLI

Both approaches create **real Iceberg tables** suitable for production-realistic benchmarking! 🎯
