#!/usr/bin/env python3
"""
Convert TPC-DS .dat files to Parquet format using schema definitions.

This script reads TPC-DS data files (pipe-delimited) and converts them
to Parquet format using the PyArrow schemas defined in TPCDSSchema.
"""

import sys
from pathlib import Path
import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.parquet as pq
from tribench.data.dataset import TPCDSSchema

def convert_table(dat_file: Path, output_file: Path, schema: pa.Schema):
    """Convert a single TPC-DS .dat file to Parquet."""
    print(f"Converting {dat_file.name}...", end=" ", flush=True)
    
    # Read CSV with schema
    table = csv.read_csv(
        dat_file,
        parse_options=csv.ParseOptions(delimiter='|'),
        convert_options=csv.ConvertOptions(
            column_names=[field.name for field in schema],
            include_columns=[field.name for field in schema],
        ),
        read_options=csv.ReadOptions(
            autogenerate_column_names=False
        )
    )
    
    # Cast to proper schema (handles type conversions)
    table = table.cast(schema)
    
    # Write to Parquet
    pq.write_table(
        table,
        output_file,
        compression='snappy',
        version='2.6'
    )
    
    row_count = len(table)
    file_size = output_file.stat().st_size / (1024 * 1024)  # MB
    print(f"{row_count:,} rows, {file_size:.2f} MB")
    
    return row_count

def main():
    if len(sys.argv) < 2:
        print("Usage: convert_tpcds_to_parquet.py <dat_directory> [output_directory]")
        sys.exit(1)
    
    dat_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else dat_dir.parent / 'parquet'
    
    if not dat_dir.exists():
        print(f"ERROR: Directory not found: {dat_dir}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("TPC-DS Data Conversion: DAT → Parquet")
    print("=" * 60)
    print(f"Input:  {dat_dir}")
    print(f"Output: {output_dir}")
    print("=" * 60)
    
    # Initialize schema
    tpcds_schema = TPCDSSchema()
    tables = tpcds_schema.get_tables()
    
    total_rows = 0
    converted_tables = []
    
    for table_name in tables:
        dat_file = dat_dir / f"{table_name}.dat"
        
        if not dat_file.exists():
            print(f"SKIP: {table_name} (file not found)")
            continue
        
        parquet_file = output_dir / f"{table_name}.parquet"
        schema = tpcds_schema.get_schema(table_name)
        
        try:
            row_count = convert_table(dat_file, parquet_file, schema)
            total_rows += row_count
            converted_tables.append(table_name)
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("=" * 60)
    print(f"Conversion complete!")
    print(f"Tables converted: {len(converted_tables)}/{len(tables)}")
    print(f"Total rows: {total_rows:,}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

if __name__ == '__main__':
    main()
