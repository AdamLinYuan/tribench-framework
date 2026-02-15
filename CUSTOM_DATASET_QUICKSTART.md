# Custom Dataset Loading - Quick Guide

## How Easy Is It? ⚡

**3 Simple Steps:**

### 1. Put Parquet Files in datasets/

```bash
datasets/
└── my-custom-dataset/
    ├── table1.parquet
    ├── table2.parquet
    └── table3.parquet
```

### 2. Load with TriBench CLI

```bash
tribench data load my-custom-dataset --catalog iceberg --schema my_schema
```

### 3. Done! ✅

The framework automatically:
- Discovers all `.parquet` files
- Reads schemas from the Parquet files
- Creates Iceberg tables
- Loads data using fast CTAS pipeline
- No registration needed!
- No schema definition needed!

## Real Example: E-Commerce Dataset

```bash
# Generated custom e-commerce dataset (already done)
datasets/ecommerce-tiny/
  ├── customers.parquet     (1,000 rows)
  ├── products.parquet      (500 rows)
  ├── orders.parquet        (5,000 rows)
  └── order_items.parquet   (15,000 rows)

# Load it
$ tribench data load ecommerce-tiny --catalog iceberg --schema ecommerce

# Output:
Auto-discovering custom dataset: ecommerce-tiny
Location: datasets/ecommerce-tiny

Discovered 4 tables:
  • customers                 1,000 rows,  6 columns,   0.02 MB
  • order_items              15,000 rows,  6 columns,   0.24 MB  
  • orders                    5,000 rows,  6 columns,   0.08 MB
  • products                    500 rows,  6 columns,   0.02 MB

Loading into iceberg.ecommerce...

✓ Custom dataset loaded successfully!
   Access via: iceberg.ecommerce.<table_name>

Loaded tables:
  - customers: 1,000 rows
  - order_items: 15,000 rows
  - orders: 5,000 rows
  - products: 500 rows
```

## Query Your Data

```sql
-- Connect to Trino
$ docker exec -it tribench-trino trino --catalog iceberg --schema ecommerce

-- Query your tables
SELECT COUNT(*) FROM customers;
SELECT * FROM products WHERE price > 100;
SELECT c.country, COUNT(o.order_id) 
FROM customers c JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.country;
```

## Run Benchmarks

```yaml
# experiments/my-custom-benchmark.yaml
name: "custom-test"
connection:
  catalog: "iceberg"
  schema: "ecommerce"
queries:
  - name: "top_customers"
    sql: |
      SELECT c.name, SUM(o.total_amount) AS revenue
      FROM customers c
      JOIN orders o ON c.customer_id = o.customer_id
      GROUP BY c.name
      ORDER BY revenue DESC
      LIMIT 10
```

```bash
tribench exp run experiments/my-custom-benchmark.yaml
```

## Supported Data Sources

### From CSV
```python
import pandas as pd
df = pd.read_csv('data.csv')
df.to_parquet('datasets/my-dataset/table1.parquet')
```

### From Database
```python
import sqlalchemy as sa
engine = sa.create_engine('postgresql://...')
df = pd.read_sql_table('table1', engine)
df.to_parquet('datasets/my-dataset/table1.parquet')
```

### From Kaggle
1. Download CSV dataset  
2. Convert to Parquet with Pandas
3. Put in datasets/ folder
4. Load with TriBench

### Generate Synthetic Data
```python
# utils/generate_custom_dataset.py already provided
python utils/generate_custom_dataset.py --customers 10000
```

## Comparison with Other Tools

**Spark:**
```scala
// Define schema
val schema = StructType(Array(
  StructField("id", IntegerType, nullable = false),
  StructField("name", StringType, nullable = true),
  // ... many lines ...
))

// Load data
val df = spark.read.schema(schema).parquet("path")

// Write to Iceberg
df.writeTo("catalog.schema.table")
  .using("iceberg")
  .createOrReplace()
```

**TriBench:**
```bash
tribench data load my-dataset --catalog iceberg --schema  my_schema
```

**Lines of Code:** Spark ~20+ | TriBench: 1 😎

## No More:
- ❌ Schema definition files
- ❌ Registry registration
- ❌ Python scripts
- ❌ SQL DDL statements
- ❌ Data type conversions

## Just:
- ✅ Drop Parquet files in folder
- ✅ Run one CLI command
- ✅ Query and benchmark immediately

That's it! 🎉
