"""
Iceberg data loading strategies.

Provides CTAS (fast) and batch INSERT (fallback) loading methods.
"""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from tribench.defaults import Defaults
from .mappings import get_column_mappings

logger = logging.getLogger(__name__)


class IcebergDataLoader:
    """Handles loading data into Iceberg tables using different strategies."""
    
    @staticmethod
    def check_tpch_catalog(cursor) -> bool:
        """
        Check if Trino's built-in tpch catalog is available.
        
        Args:
            cursor: Database cursor
        
        Returns:
            True if tpch catalog is available, False otherwise
        """
        try:
            cursor.execute("SHOW SCHEMAS FROM tpch")
            schemas = [row[0] for row in cursor.fetchall()]
            available = 'tiny' in schemas or 'sf1' in schemas
            if available:
                logger.info("✓ TPC-H catalog available - using fast CTAS loading")
            return available
        except Exception as e:
            logger.debug(f"TPC-H catalog not available: {e}")
            return False
    
    @staticmethod
    def load_via_ctas(
        cursor,
        table_name: str,
        tpch_scale_factor: str,
        partitioning: Optional[List[str]] = None,
        storage_location: Optional[str] = None
    ) -> int:
        """
        Load table using CTAS from Trino's built-in tpch catalog.
        
        This is the FASTEST method - data is generated on-the-fly by Trino
        and directly written to Iceberg format. No file upload needed.
        
        Args:
            cursor: Database cursor
            table_name: Table name to create
            tpch_scale_factor: TPC-H schema (e.g., 'tiny', 'sf1')
            partitioning: Optional partition columns
            storage_location: Optional S3 storage location
        
        Returns:
            Number of rows loaded
        """
        # Drop table if exists (for clean reload)
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        except Exception as e:
            logger.debug(f"Drop table note: {e}")
        
        # Build CTAS statement with properties
        properties = ["format = 'PARQUET'"]
        
        if partitioning:
            # Iceberg partitioning syntax
            partition_cols = ", ".join(f"'{col}'" for col in partitioning)
            properties.append(f"partitioning = ARRAY[{partition_cols}]")
        
        if storage_location:
            table_location = f"{storage_location.rstrip('/')}/{table_name}"
            properties.append(f"location = '{table_location}'")
        
        properties_sql = ", ".join(properties)
        
        # Build SELECT clause with column aliases for TPC-H standard names
        column_mappings = get_column_mappings(table_name)
        if column_mappings:
            # Use aliases: "orderkey AS l_orderkey, partkey AS l_partkey, ..."
            select_cols = ", ".join(
                f"{src} AS {dst}" for src, dst in column_mappings.items()
            )
        else:
            select_cols = "*"
        
        # CTAS: Create Table As Select from tpch catalog with renamed columns
        ctas_sql = f"""
            CREATE TABLE {table_name}
            WITH ({properties_sql})
            AS SELECT {select_cols} FROM tpch.{tpch_scale_factor}.{table_name}
        """
        
        logger.debug(f"CTAS SQL:\n{ctas_sql}")
        cursor.execute(ctas_sql)
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        return row_count
    
    @staticmethod
    def load_via_batch_insert(
        cursor,
        table_name: str,
        parquet_file: Path,
        table_schema: pa.Schema
    ) -> int:
        """
        Fallback data loading using batch inserts.
        
        Used when CTAS from tpch catalog is not available.
        
        Args:
            cursor: Database cursor
            table_name: Table name
            parquet_file: Path to Parquet file
            table_schema: Expected schema
        
        Returns:
            Number of rows loaded
        """
        # Read Parquet file
        parquet_table = pq.read_table(parquet_file)
        row_count = parquet_table.num_rows
        df = parquet_table.to_pandas()
        
        # Column names for INSERT
        column_names = [field.name for field in table_schema]
        columns_sql = ", ".join(column_names)
        
        # Determine optimal batch size based on table size and row width
        # Larger batches = fewer roundtrips = faster
        if row_count < 1000:
            batch_size = row_count  # Single batch for small tables
        elif row_count < 10000:
            batch_size = Defaults.Retry.DATA_BATCH_SIZE_MEDIUM
        elif row_count < 100000:
            batch_size = Defaults.Retry.DATA_BATCH_SIZE_LARGE
        else:
            batch_size = Defaults.Retry.DATA_BATCH_SIZE_XLARGE
        
        logger.info(f"  Inserting {row_count:,} rows (batch size: {batch_size})")
        
        total_inserted = 0
        
        # Pre-create type lookup for faster formatting
        type_lookup = {field.name: field.type for field in table_schema}
        
        for start_idx in range(0, len(df), batch_size):
            end_idx = min(start_idx + batch_size, len(df))
            batch = df.iloc[start_idx:end_idx]
            
            # Build VALUES clause efficiently
            values_rows = []
            for _, row in batch.iterrows():
                formatted_values = []
                for col_name in column_names:
                    value = row[col_name]
                    arrow_type = type_lookup[col_name]
                    formatted_value = IcebergDataLoader._format_value(value, arrow_type)
                    formatted_values.append(formatted_value)
                values_rows.append(f"({', '.join(formatted_values)})")
            
            values_sql = ",\n".join(values_rows)
            insert_sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES\n{values_sql}"
            
            try:
                cursor.execute(insert_sql)
                total_inserted += len(batch)
            except Exception as e:
                logger.error(f"Batch insert failed at row {start_idx}: {e}")
                raise
        
        return total_inserted
    
    @staticmethod
    def _format_value(value, arrow_type: pa.DataType) -> str:
        """
        Format a value for SQL INSERT statement.
        
        Args:
            value: The value to format
            arrow_type: PyArrow data type
        
        Returns:
            SQL-formatted value string
        """
        # NULL check
        if value is None:
            return "NULL"
        
        # Check for pandas/numpy NA types
        try:
            if pd.isna(value):
                return "NULL"
        except (TypeError, ValueError):
            pass
        
        # String types
        if pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
        
        # Date types
        if pa.types.is_date(arrow_type):
            return f"DATE '{value}'"
        
        # Timestamp types
        if pa.types.is_timestamp(arrow_type):
            return f"TIMESTAMP '{value}'"
        
        # All other types (numeric, etc.)
        return str(value)
