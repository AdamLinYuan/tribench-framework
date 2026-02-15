# TPC-DS Benchmark

TPC-DS (Transaction Processing Performance Council Decision Support) is a decision support benchmark that models the decision support functions of a retail product supplier.

## Overview

- **Benchmark Type**: Decision Support / Data Warehousing
- **Tables**: 24 (7 fact tables, 17 dimension tables)
- **Queries**: 99 templates varying in complexity
- **Dataset Sizes**: Scale factors from 1GB to 100TB

## Schema

The TPC-DS schema models:
- Sales channels: Store, Catalog, Web
- Operations: Sales,Returns, Inventory
- Dimensions: Time, Customer, Product, Store, Promotion

### Fact Tables (7)
- `store_sales` - In-store purchases
- `store_returns` - In-store returns
- `catalog_sales` - Catalog orders
- `catalog_returns` - Catalog returns
- `web_sales` - Online purchases
- `web_returns` - Online returns
- `inventory` - Warehouse stock levels

### Dimension Tables (17)
- `date_dim`, `time_dim` - Temporal dimensions
- `customer`, `customer_address`, `customer_demographics` - Customer data
- `item`, `promotion`, `warehouse` - Product data
- `store`, `call_center`, `catalog_page`, `web_site`, `web_page` - Channel data
- `household_demographics`, `income_band`, `reason`, `ship_mode` - Supporting dimensions

## Getting Started

### 1. Generate Data

```bash
# Generate scale factor 1 (1GB dataset)
./utils/generate_tpcds.sh 1

# Or use the Python converter directly
./utils/convert_tpcds_to_parquet.py datasets/tpcds-sf1/dat
```

### 2. Load Data

```bash
tribench data load tpcds-sf1 \
  --catalog iceberg \
  --schema tpcds \
  --partition store_sales:ss_sold_date_sk \
  --partition catalog_sales:cs_sold_date_sk \
  --partition web_sales:ws_sold_date_sk
```

### 3. Run Benchmark

```bash
# Run all available queries
tribench exp run experiments/tpcds-sf1.yaml

# Run specific query
tribench exp run experiments/tpcds-sf1.yaml --query apps/tpcds/queries/q01.sql
```

## Dataset Sizes

| Scale Factor | Raw Size | Parquet Size | Store Sales Rows | Typical Use Case |
|--------------|----------|--------------|------------------|------------------|
| 1            | ~1 GB    | ~300 MB      | ~2.8M           | Development      |
| 10           | ~10 GB   | ~3 GB        | ~28M            | Testing          |
| 100          | ~100 GB  | ~30 GB       | ~280M           | Small Production |
| 1000         | ~1 TB    | ~300 GB      | ~2.8B           | Production       |
| 10000        | ~10 TB   | ~3 TB        | ~28B            | Large Scale      |
| 100000       | ~100 TB  | ~30 TB       | ~280B           | Very Large Scale |

## Query Characteristics

TPC-DS queries fall into several categories:

1. **Reporting Queries** - Basic aggregations, simple joins
2. **Ad-hoc Queries** - Complex joins, multiple predicates
3. **Iterative OLAP** - ROLLUP/CUBE, windowing
4. **Data Mining** - Statistical functions, complex analytics

Complexity ranges from simple 2-table joins to 10+ table joins with nested subqueries and CTEs.

## Performance Tuning

### Partitioning Recommendations

```yaml
partition_specs:
  store_sales: ['ss_sold_date_sk']
  catalog_sales: ['cs_sold_date_sk']
  web_sales: ['ws_sold_date_sk']
  store_returns: ['sr_returned_date_sk']
  catalog_returns: ['cr_returned_date_sk']
  web_returns: ['wr_returned_date_sk']
  inventory: ['inv_date_sk']
```

### Statistics Collection

Ensure statistics are collected on key columns:
- Foreign keys (all `_sk` columns)
- Date columns
- High-cardinality dimensions

### Query Optimization

- Most queries benefit from partition pruning on date dimensions
- Consider materialized views for frequently-accessed aggregations
- Broadcast joins work well for small dimension tables
- Large fact table joins may need repartitioning

## Validation

TPC-DS includes query result validation. Compare your results against:
- Official TPC-DS qualification kit
- Known result sets for specific scale factors
- Cross-validation between different engines

## Compliance

For official TPC-DS compliance:
1. Use official data generator (dsdgen)
2. Run all 99 queries as specified
3. Meet performance and scalability requirements
4. Follow full disclosure requirements
5. Submit for TPC audit

**Note**: This implementation is for benchmarking and testing purposes. Full TPC-DS compliance requires adherence to the complete specification.

## References

- TPC-DS Specification v3.2.0: http://www.tpc.org/tpcds/
- Official Tools: https://github.com/databricks/tpcds-kit
- Query Semantics: Appendix A of TPC-DS specification
- Best Practices: http://www.tpc.org/information/benchmarks.asp

## Support

For issues or questions:
- Schema definitions: `lib/tribench/data/dataset/schema.py`
- Queries: `apps/tpcds/queries/`
- Data generation: `utils/generate_tpcds.sh`
- Configuration: `experiments/tpcds-*.yaml`
