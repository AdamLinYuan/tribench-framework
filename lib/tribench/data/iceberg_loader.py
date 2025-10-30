"""
Iceberg Table Creation and Data Loading for TriBench framework.

This module provides functionality to:
- Create Iceberg tables in Trino
- Load TPC-H Parquet data into Iceberg format
- Handle schema inference from Parquet files
- Configure table properties (partitioning, format version, storage)
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import pyarrow as pa
import pyarrow.parquet as pq
from trino.dbapi import connect

from tribench.data.dataset import DatasetSchema, TPCHSchema

logger = logging.getLogger(__name__)


class IcebergDataLoader:
    """
    Loads datasets into Iceberg tables in Trino.
    
    Creates Iceberg tables with proper configuration for:
    - Parquet file format
    - Optional partitioning
    - S3/MinIO storage locations
    - Schema evolution support
    """
    
    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize Iceberg data loader.
        
        Args:
            connection_params: Trino connection parameters
                - host: Trino host (default: localhost)
                - port: Trino port (default: 8080)
                - user: Username (default: admin)
        """
        self.connection_params = connection_params
        self._connection = None
    
    def load_dataset(
        self,
        dataset_path: Path,
        dataset_schema: DatasetSchema,
        catalog: str = 'iceberg',
        schema: str = 'tpch',
        storage_location: Optional[str] = None,
        partition_specs: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, int]:
        """
        Load dataset into Iceberg tables in Trino.
        
        Args:
            dataset_path: Path to Parquet files
            dataset_schema: DatasetSchema instance (e.g., TPCHSchema)
            catalog: Trino Iceberg catalog name (default: 'iceberg')
            schema: Schema name to create (default: 'tpch')
            storage_location: Optional S3 location (e.g., 's3://warehouse/tpch/')
            partition_specs: Optional dict mapping table names to partition column lists
                            Example: {'lineitem': ['l_shipdate'], 'orders': ['o_orderdate']}
        
        Returns:
            Dict mapping table names to row counts
        """
        benchmark_type = dataset_schema.get_benchmark_type().value
        logger.info(f"Loading {benchmark_type.upper()} dataset into Iceberg format")
        logger.info(f"Source: {dataset_path}")
        logger.info(f"Target: {catalog}.{schema}")
        
        # Connect to Trino
        conn = self._get_connection(catalog, schema)
        cursor = conn.cursor()
        
        # Create schema if it doesn't exist
        self._create_schema(cursor, schema, storage_location)
        
        row_counts = {}
        partition_specs = partition_specs or {}
        
        # Load each table
        for parquet_file in sorted(dataset_path.glob("*.parquet")):
            table_name = parquet_file.stem
            
            if table_name not in dataset_schema.get_tables():
                logger.warning(f"Skipping unknown table: {table_name}")
                continue
            
            logger.info(f"Loading Iceberg table: {table_name}")
            
            try:
                # Get table schema from dataset schema
                table_schema = dataset_schema.get_schema(table_name)
                
                # Get partition specification for this table
                partitioning = partition_specs.get(table_name)
                
                # Create Iceberg table
                self._create_iceberg_table(
                    cursor,
                    table_name,
                    table_schema,
                    partitioning,
                    storage_location
                )
                
                # Load data from Parquet file
                row_count = self._load_data_from_parquet(
                    cursor,
                    table_name,
                    parquet_file,
                    table_schema
                )
                
                row_counts[table_name] = row_count
                logger.info(f"✓ Loaded {table_name}: {row_count} rows")
                
            except Exception as e:
                logger.error(f"Failed to load {table_name}: {e}", exc_info=True)
                raise
        
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully loaded {len(row_counts)} Iceberg tables")
        return row_counts
    
    def load_tpch_dataset(
        self,
        dataset_path: Path,
        catalog: str = 'iceberg',
        schema: str = 'tpch',
        storage_location: Optional[str] = None,
        use_partitioning: bool = True
    ) -> Dict[str, int]:
        """
        Load TPC-H dataset into Iceberg tables with recommended partitioning.
        
        Args:
            dataset_path: Path to TPC-H Parquet files
            catalog: Trino Iceberg catalog name
            schema: Schema name to create
            storage_location: Optional S3 location
            use_partitioning: Whether to partition large tables (lineitem, orders)
        
        Returns:
            Dict mapping table names to row counts
        """
        tpch_schema = TPCHSchema()
        
        # Default partitioning for large tables
        partition_specs = {}
        if use_partitioning:
            partition_specs = {
                'lineitem': ['l_shipdate'],
                'orders': ['o_orderdate']
            }
        
        return self.load_dataset(
            dataset_path=dataset_path,
            dataset_schema=tpch_schema,
            catalog=catalog,
            schema=schema,
            storage_location=storage_location,
            partition_specs=partition_specs
        )
    
    def _get_connection(self, catalog: str, schema: str):
        """Create Trino connection."""
        return connect(
            host=self.connection_params.get('host', 'localhost'),
            port=self.connection_params.get('port', 8080),
            user=self.connection_params.get('user', 'admin'),
            catalog=catalog,
            schema=schema
        )
    
    def _create_schema(self, cursor, schema: str, storage_location: Optional[str] = None):
        """Create schema if it doesn't exist."""
        try:
            if storage_location:
                # Note: Specifying location requires S3 support in Hive Metastore
                cursor.execute(
                    f"CREATE SCHEMA IF NOT EXISTS {schema} "
                    f"WITH (location = '{storage_location}')"
                )
            else:
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            
            logger.info(f"✓ Schema ready: {schema}")
        except Exception as e:
            # Schema might already exist
            logger.debug(f"Schema creation note: {e}")
    
    def _create_iceberg_table(
        self,
        cursor,
        table_name: str,
        table_schema: pa.Schema,
        partitioning: Optional[List[str]] = None,
        storage_location: Optional[str] = None
    ):
        """
        Create Iceberg table with specified schema and properties.
        
        Args:
            cursor: Database cursor
            table_name: Table name
            table_schema: PyArrow schema
            partitioning: List of partition column names
            storage_location: Optional S3 storage location
        """
        # Drop table if exists (for clean reload)
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        except Exception as e:
            logger.debug(f"Drop table note: {e}")
        
        # Convert PyArrow schema to SQL column definitions
        column_defs = []
        for field in table_schema:
            sql_type = self._arrow_to_trino_type(field.type)
            column_defs.append(f"{field.name} {sql_type}")
        
        columns_sql = ",\n  ".join(column_defs)
        
        # Build CREATE TABLE statement
        create_sql = f"CREATE TABLE {table_name} (\n  {columns_sql}\n)"
        
        # Add table properties
        properties = []
        
        # File format
        properties.append("format = 'PARQUET'")
        
        # Partitioning
        if partitioning:
            partition_cols = ", ".join(partitioning)
            properties.append(f"partitioning = ARRAY['{partition_cols}']")
        
        # Storage location
        if storage_location:
            table_location = f"{storage_location.rstrip('/')}/{table_name}"
            properties.append(f"location = '{table_location}'")
        
        if properties:
            properties_sql = ", ".join(properties)
            create_sql += f"\nWITH ({properties_sql})"
        
        logger.debug(f"Creating table with SQL:\n{create_sql}")
        cursor.execute(create_sql)
        logger.info(f"✓ Created Iceberg table: {table_name}")
    
    def _load_data_from_parquet(
        self,
        cursor,
        table_name: str,
        parquet_file: Path,
        table_schema: pa.Schema
    ) -> int:
        """
        Load data from Parquet file into Iceberg table.
        
        Args:
            cursor: Database cursor
            table_name: Table name
            parquet_file: Path to Parquet file
            table_schema: Expected schema
        
        Returns:
            Number of rows loaded
        """
        # Read Parquet file to get row count
        parquet_table = pq.read_table(parquet_file)
        row_count = parquet_table.num_rows
        
        # Prepare column list
        column_names = [field.name for field in table_schema]
        columns_sql = ", ".join(column_names)
        
        # Read data and insert in batches
        # For large files, we'd want to batch this, but for TPC-H tiny/SF1 it's manageable
        logger.info(f"Inserting {row_count} rows from {parquet_file.name}...")
        
        # Convert to pandas for easier row iteration (could optimize this further)
        df = parquet_table.to_pandas()
        
        # Batch size for inserts
        batch_size = 1000
        total_inserted = 0
        
        for start_idx in range(0, len(df), batch_size):
            end_idx = min(start_idx + batch_size, len(df))
            batch = df.iloc[start_idx:end_idx]
            
            # Build VALUES clause
            values_rows = []
            for _, row in batch.iterrows():
                # Format values for SQL
                formatted_values = []
                for i, field in enumerate(table_schema):
                    value = row.iloc[i]
                    formatted_value = self._format_value_for_sql(value, field.type)
                    formatted_values.append(formatted_value)
                
                values_rows.append(f"({', '.join(formatted_values)})")
            
            values_sql = ",\n".join(values_rows)
            
            # Execute batch insert
            insert_sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES\n{values_sql}"
            
            try:
                cursor.execute(insert_sql)
                total_inserted += len(batch)
                
                if total_inserted % 10000 == 0:
                    logger.info(f"  Inserted {total_inserted}/{row_count} rows...")
            except Exception as e:
                logger.error(f"Failed to insert batch: {e}")
                logger.debug(f"Failed SQL (first 500 chars): {insert_sql[:500]}")
                raise
        
        return total_inserted
    
    def _arrow_to_trino_type(self, arrow_type: pa.DataType) -> str:
        """
        Convert PyArrow type to Trino SQL type.
        
        Args:
            arrow_type: PyArrow data type
        
        Returns:
            Trino SQL type string
        """
        if pa.types.is_int8(arrow_type) or pa.types.is_int16(arrow_type):
            return "SMALLINT"
        elif pa.types.is_int32(arrow_type):
            return "INTEGER"
        elif pa.types.is_int64(arrow_type):
            return "BIGINT"
        elif pa.types.is_float32(arrow_type):
            return "REAL"
        elif pa.types.is_float64(arrow_type):
            return "DOUBLE"
        elif pa.types.is_decimal(arrow_type):
            precision = arrow_type.precision
            scale = arrow_type.scale
            return f"DECIMAL({precision}, {scale})"
        elif pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
            return "VARCHAR"
        elif pa.types.is_date(arrow_type):
            return "DATE"
        elif pa.types.is_timestamp(arrow_type):
            return "TIMESTAMP"
        else:
            # Default to VARCHAR for unknown types
            logger.warning(f"Unknown PyArrow type {arrow_type}, defaulting to VARCHAR")
            return "VARCHAR"
    
    def _format_value_for_sql(self, value, arrow_type: pa.DataType) -> str:
        """
        Format a value for SQL INSERT statement.
        
        Args:
            value: The value to format
            arrow_type: PyArrow data type
        
        Returns:
            SQL-formatted value string
        """
        import pandas as pd
        import numpy as np
        
        # Handle NULL/None/NaN
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "NULL"
        
        # Handle timestamps
        if pd.isna(value):
            return "NULL"
        
        # String types need quoting and escaping
        if pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
            # Escape single quotes
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
        
        # Date types
        elif pa.types.is_date(arrow_type):
            return f"DATE '{value}'"
        
        # Timestamp types
        elif pa.types.is_timestamp(arrow_type):
            return f"TIMESTAMP '{value}'"
        
        # Numeric types (no quoting needed)
        else:
            return str(value)
    
    def collect_iceberg_metadata(
        self,
        catalog: str,
        schema: str,
        tables: List[str]
    ) -> Dict[str, Any]:
        """
        Collect Iceberg-specific metadata for loaded tables.
        
        Args:
            catalog: Iceberg catalog name
            schema: Schema name
            tables: List of table names
        
        Returns:
            Dict with Iceberg metadata:
                - snapshot_ids: Dict[table_name, snapshot_id]
                - snapshot_timestamps: Dict[table_name, timestamp]
                - manifest_counts: Dict[table_name, count]
                - format_version: Iceberg format version
                - storage_location: Storage base location
        """
        conn = self._get_connection(catalog, schema)
        cursor = conn.cursor()
        
        snapshot_ids = {}
        snapshot_timestamps = {}
        manifest_counts = {}
        format_version = None
        storage_location = None
        
        for table_name in tables:
            try:
                # Get current snapshot information
                snapshot_query = f"""
                    SELECT snapshot_id, committed_at
                    FROM "{catalog}"."{schema}"."{table_name}$snapshots"
                    ORDER BY committed_at DESC
                    LIMIT 1
                """
                cursor.execute(snapshot_query)
                snapshot_row = cursor.fetchone()
                
                if snapshot_row:
                    snapshot_ids[table_name] = snapshot_row[0]
                    snapshot_timestamps[table_name] = str(snapshot_row[1])
                
                # Get manifest count from files table
                files_query = f"""
                    SELECT COUNT(DISTINCT manifest_file)
                    FROM "{catalog}"."{schema}"."{table_name}$files"
                """
                cursor.execute(files_query)
                manifest_row = cursor.fetchone()
                
                if manifest_row and manifest_row[0]:
                    manifest_counts[table_name] = manifest_row[0]
                
                # Get table properties (format version, location) - only once
                if format_version is None or storage_location is None:
                    try:
                        props_query = f"SHOW CREATE TABLE {table_name}"
                        cursor.execute(props_query)
                        create_stmt = cursor.fetchone()
                        
                        if create_stmt:
                            stmt_text = create_stmt[0]
                            # Extract format version from CREATE TABLE statement
                            if 'format_version' in stmt_text.lower():
                                # Parse format version from properties
                                import re
                                match = re.search(r"format_version\s*=\s*['\"]?(\d+)", stmt_text, re.IGNORECASE)
                                if match:
                                    format_version = int(match.group(1))
                            
                            # Extract location
                            if 'location' in stmt_text.lower():
                                match = re.search(r"location\s*=\s*['\"]([^'\"]+)", stmt_text, re.IGNORECASE)
                                if match:
                                    loc = match.group(1)
                                    # Get base location (remove table-specific path)
                                    if '/' + table_name in loc:
                                        storage_location = loc.split('/' + table_name)[0]
                                    else:
                                        storage_location = loc
                    except Exception as e:
                        logger.debug(f"Could not extract table properties: {e}")
                
            except Exception as e:
                logger.debug(f"Could not collect metadata for {table_name}: {e}")
        
        cursor.close()
        conn.close()
        
        # Default format version if not detected
        if format_version is None:
            format_version = 2  # Iceberg v2 is default in modern systems
        
        return {
            'snapshot_ids': snapshot_ids,
            'snapshot_timestamps': snapshot_timestamps,
            'manifest_counts': manifest_counts,
            'format_version': format_version,
            'storage_location': storage_location
        }


def create_iceberg_loader(config: Optional[Dict] = None) -> IcebergDataLoader:
    """
    Factory function to create an IcebergDataLoader with configuration.
    
    Args:
        config: Optional configuration dict. If None, uses defaults.
    
    Returns:
        Configured IcebergDataLoader instance
    """
    if config is None:
        config = {}
    
    connection_params = {
        'host': config.get('host', 'localhost'),
        'port': config.get('port', 8080),
        'user': config.get('user', 'admin')
    }
    
    return IcebergDataLoader(connection_params)
