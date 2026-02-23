# TPC-DS Queries

This directory contains SQL queries for the TPC-DS (Transaction Processing Performance Council Decision Support) benchmark.

## Overview

TPC-DS is a decision support benchmark that models the operations of a retail product supplier. It consists of:
- **24 tables** (7 fact tables, 17 dimension tables)
- **99 query templates** with varying complexity
- Uses ad-hoc, reporting, and iterative OLAP query patterns

## Query Coverage

Currently included queries:
- **q01.sql** - Customer return analysis
- **q03.sql** - Year-over-year sales by brand
- **q07.sql** - Promotional sales analysis
- **q19.sql** - Multi-channel brand sales
- **q27.sql** - Demographic-based sales with ROLLUP
- **q42.sql** - Category sales comparison
- **q52.sql** - Brand sales by year
- **q55.sql** - Manager-specific brand sales
- **q73.sql** - Customer purchase pattern analysis
- **q96.sql** - Time-based store sales

## Getting All 99 Queries

To get the complete set of TPC-DS queries:

### Option 1: Official TPC-DS Tools

```bash
# Clone TPC-DS kit
git clone https://github.com/databricks/tpcds-kit.git

# Query templates are in: tpcds-kit/query_templates/
# Already parameterized queries: tpcds-kit/sample_queries/
```

### Option 2: Use dsqgen Tool

```bash
cd tpcds-kit/tools
make

# Generate all 99 queries for a specific dialect
./dsqgen \
    -DIRECTORY ../query_templates \
    -INPUT ../query_templates/templates.lst \
    -DIALECT trino \
    -OUTPUT_DIR ../../apps/tpcds/queries
```

### Option 3: Manual Download

Download from official TPC website:
- Specification: http://www.tpc.org/tpcds/
- Query templates: Included in specification document (Appendix A)

## Query Categories

TPC-DS queries are grouped by pattern:

1. **Reporting Queries** (q01, q03, q07, q42, q52, q55)
   - Simple aggregations and groupings
   - Basic filtering

2. **Ad-hoc Queries** (q19, q27)
   - Complex joins
   - Dynamic filtering
   - ROLLUP and CUBE operations

3. **Iterative OLAP** (q73, q96)
   - Multiple aggregation levels
   - Complex correlated subqueries
   - Window functions

4. **Data Mining** (q34, q63, q74, etc.)
   - Statistical functions
   - Advanced analytics

## Query Complexity

- **Low Complexity**: Queries with 2-3 table joins (q3, q7, q52, q55)
- **Medium Complexity**: Queries with 4-6 table joins (q19, q27, q42)
- **High Complexity**: Queries with 7+ table joins and subqueries (q1, q73)
- **Very High Complexity**: Queries with nested subqueries and CTEs (q14, q39, q77)

## Usage with TriBench

### Run single query:
```bash
tribench exp run experiments/tpcds-validation.yaml \
  --query apps/tpcds/queries/q01.sql
```

### Run all queries:
```bash
tribench exp run experiments/tpcds-sf1.yaml
```

### Run specific subset:
```yaml
# experiments/tpcds-subset.yaml
name: "tpcds-reporting"
query_files:
  - "apps/tpcds/queries/q01.sql"
  - "apps/tpcds/queries/q03.sql"
  - "apps/tpcds/queries/q07.sql"
```

## Customization

TPC-DS queries use substitution parameters. Default values are provided in the queries,
but you can customize them:

- Year ranges: 1998-2003
- Months: 1-12
- Manager IDs: 1-100
- States, counties: Based on your data distribution

## Notes

- Queries are adapted for Trino SQL dialect
- Some queries require approximate aggregation functions
- Complex queries may need query optimization hints
- Partition pruning significantly improves performance on date-partitioned fact tables

## References

- TPC-DS Specification v3.2.0: http://www.tpc.org/tpcds/
- Query semantics: http://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v3.2.0.pdf
- Databricks TPC-DS Kit: https://github.com/databricks/tpcds-kit
