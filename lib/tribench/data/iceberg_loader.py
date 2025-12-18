"""
Iceberg Table Creation and Data Loading for TriBench framework.

This module provides functionality to:
- Create Iceberg tables in Trino
- Load TPC-H Parquet data into Iceberg format
- Handle schema inference from Parquet files
- Configure table properties (partitioning, format version, storage)

Performance Optimizations:
- Uses CTAS (CREATE TABLE AS SELECT) from Trino's built-in TPC-H catalog
- Falls back to batch INSERT from Parquet files if CTAS unavailable
- The built-in tpch connector generates data on-the-fly, no file upload needed
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from trino.dbapi import connect

from tribench.data.dataset import DatasetSchema, TPCHSchema
from tribench.defaults import Defaults
from tribench.config import ConnectionConfig

logger = logging.getLogger(__name__)

# Map dataset names to TPC-H scale factors
TPCH_SCALE_FACTOR_MAP = {
    'tpch-tiny': 'tiny',
    'tpch-sf0_01': 'tiny',  # ~0.01 SF maps to tiny
    'tpch-sf0.01': 'tiny',
    'tpch-sf1': 'sf1',
    'tpch-sf10': 'sf10',
    'tpch-sf100': 'sf100',
}

# Column mappings from Trino's tpch connector to TPC-H standard names
# Trino uses short names, TPC-H standard uses prefix (l_, o_, c_, etc.)
TPCH_COLUMN_MAPPINGS = {
    'nation': {
        'nationkey': 'n_nationkey',
        'name': 'n_name',
        'regionkey': 'n_regionkey',
        'comment': 'n_comment',
    },
    'region': {
        'regionkey': 'r_regionkey',
        'name': 'r_name',
        'comment': 'r_comment',
    },
    'customer': {
        'custkey': 'c_custkey',
        'name': 'c_name',
        'address': 'c_address',
        'nationkey': 'c_nationkey',
        'phone': 'c_phone',
        'acctbal': 'c_acctbal',
        'mktsegment': 'c_mktsegment',
        'comment': 'c_comment',
    },
    'supplier': {
        'suppkey': 's_suppkey',
        'name': 's_name',
        'address': 's_address',
        'nationkey': 's_nationkey',
        'phone': 's_phone',
        'acctbal': 's_acctbal',
        'comment': 's_comment',
    },
    'part': {
        'partkey': 'p_partkey',
        'name': 'p_name',
        'mfgr': 'p_mfgr',
        'brand': 'p_brand',
        'type': 'p_type',
        'size': 'p_size',
        'container': 'p_container',
        'retailprice': 'p_retailprice',
        'comment': 'p_comment',
    },
    'partsupp': {
        'partkey': 'ps_partkey',
        'suppkey': 'ps_suppkey',
        'availqty': 'ps_availqty',
        'supplycost': 'ps_supplycost',
        'comment': 'ps_comment',
    },
    'orders': {
        'orderkey': 'o_orderkey',
        'custkey': 'o_custkey',
        'orderstatus': 'o_orderstatus',
        'totalprice': 'o_totalprice',
        'orderdate': 'o_orderdate',
        'orderpriority': 'o_orderpriority',
        'clerk': 'o_clerk',
        'shippriority': 'o_shippriority',
        'comment': 'o_comment',
    },
    'lineitem': {
        'orderkey': 'l_orderkey',
        'partkey': 'l_partkey',
        'suppkey': 'l_suppkey',
        'linenumber': 'l_linenumber',
        'quantity': 'l_quantity',
        'extendedprice': 'l_extendedprice',
        'discount': 'l_discount',
        'tax': 'l_tax',
        'returnflag': 'l_returnflag',
        'linestatus': 'l_linestatus',
        'shipdate': 'l_shipdate',
        'commitdate': 'l_commitdate',
        'receiptdate': 'l_receiptdate',
        'shipinstruct': 'l_shipinstruct',
        'shipmode': 'l_shipmode',
        'comment': 'l_comment',
    },
}


class IcebergDataLoader:
    """
    Loads datasets into Iceberg tables in Trino.
    
    Creates Iceberg tables with proper configuration for:
    - Parquet file format
    - Optional partitioning
    - S3/MinIO storage locations
    - Schema evolution support
    
    Performance:
    - Uses CTAS from Trino's built-in tpch catalog (fastest)
    - Falls back to batch INSERT from Parquet files if tpch catalog unavailable
    """
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
        """
        Initialize Iceberg data loader.
        
        Args:
            connection_params: Trino connection parameters
                - host: Trino host (default: localhost)
                - port: Trino port (default: 8080)
                - user: Username (default: admin)
        """
        if connection_params is None:
            self.connection_params = ConnectionConfig.from_defaults()
        elif isinstance(connection_params, ConnectionConfig):
            self.connection_params = connection_params
        elif isinstance(connection_params, dict):
            self.connection_params = ConnectionConfig.from_dict(connection_params)
        else:
            raise TypeError(
                f"connection_params must be dict, ConnectionConfig, or None, got {type(connection_params)}"
            )
        self._connection = None
        
        # Check if tpch catalog is available (will be set during load)
        self._tpch_catalog_available = None
    
    def _check_tpch_catalog(self, cursor) -> bool:
        """Check if Trino's built-in tpch catalog is available."""
        if self._tpch_catalog_available is not None:
            return self._tpch_catalog_available
        
        try:
            cursor.execute("SHOW SCHEMAS FROM tpch")
            schemas = [row[0] for row in cursor.fetchall()]
            self._tpch_catalog_available = 'tiny' in schemas or 'sf1' in schemas
            if self._tpch_catalog_available:
                logger.info("✓ TPC-H catalog available - using fast CTAS loading")
            return self._tpch_catalog_available
        except Exception as e:
            logger.debug(f"TPC-H catalog not available: {e}")
            self._tpch_catalog_available = False
            return False
    
    def _get_tpch_scale_factor(self, dataset_name: str) -> Optional[str]:
        """
        Map dataset name to TPC-H scale factor schema.
        
        Args:
            dataset_name: Dataset name (e.g., 'tpch-tiny', 'tpch-sf1')
        
        Returns:
            Schema name in tpch catalog (e.g., 'tiny', 'sf1') or None
        """
        # Direct mapping
        if dataset_name in TPCH_SCALE_FACTOR_MAP:
            return TPCH_SCALE_FACTOR_MAP[dataset_name]
        
        # Try to extract scale factor from name
        match = re.search(r'sf(\d+)', dataset_name.lower())
        if match:
            sf = match.group(1)
            return f'sf{sf}'
        
        if 'tiny' in dataset_name.lower():
            return 'tiny'
        
        return None
    
    def load_dataset(
        self,
        dataset_path: Path,
        dataset_schema: DatasetSchema,
        catalog: str = 'iceberg',
        schema: str = 'tpch',
        storage_location: Optional[str] = None,
        partition_specs: Optional[Dict[str, List[str]]] = None,
        fast_mode: bool = True,
        dataset_name: Optional[str] = None
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
            fast_mode: Use optimized CTAS loading if available (default: True)
            dataset_name: Optional dataset name for TPC-H catalog matching
        
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
        
        # Check if we can use fast CTAS loading from tpch catalog
        tpch_sf = None
        if fast_mode and dataset_name:
            tpch_sf = self._get_tpch_scale_factor(dataset_name)
            if tpch_sf and self._check_tpch_catalog(cursor):
                logger.info(f"Using fast CTAS from tpch.{tpch_sf}")
            else:
                tpch_sf = None
                logger.info("Using batch INSERT loading (tpch catalog not available)")
        
        if not fast_mode:
            logger.info("Using batch INSERT loading (fast_mode disabled)")
        
        row_counts = {}
        partition_specs = partition_specs or {}
        
        # Get list of tables from schema
        tables_to_load = dataset_schema.get_tables()
        
        # Load tables using CTAS or batch INSERT
        for table_name in tables_to_load:
            logger.info(f"Loading Iceberg table: {table_name}")
            
            try:
                # Get partition specification for this table
                partitioning = partition_specs.get(table_name)
                
                if tpch_sf:
                    # Fast path: CTAS from tpch catalog
                    row_count = self._load_via_ctas(
                        cursor,
                        table_name,
                        tpch_sf,
                        partitioning,
                        storage_location
                    )
                else:
                    # Slow path: batch INSERT from Parquet file
                    parquet_file = dataset_path / f"{table_name}.parquet"
                    if not parquet_file.exists():
                        logger.warning(f"Parquet file not found: {parquet_file}")
                        continue
                    
                    table_schema = dataset_schema.get_schema(table_name)
                    
                    # Create Iceberg table
                    self._create_iceberg_table(
                        cursor,
                        table_name,
                        table_schema,
                        partitioning,
                        storage_location
                    )
                    
                    # Load data from Parquet file
                    row_count = self._load_data_fast(
                        cursor,
                        table_name,
                        parquet_file,
                        table_schema
                    )
                
                row_counts[table_name] = row_count
                logger.info(f"✓ Loaded {table_name}: {row_count:,} rows")
                
            except Exception as e:
                logger.error(f"Failed to load {table_name}: {e}", exc_info=True)
                raise
        
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully loaded {len(row_counts)} Iceberg tables")
        return row_counts
    
    def _load_via_ctas(
        self,
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
        column_mappings = TPCH_COLUMN_MAPPINGS.get(table_name, {})
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
    
    def _load_data_fast(
        self,
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
                    formatted_value = self._format_value(value, arrow_type)
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
    
    def _format_value(self, value, arrow_type: pa.DataType) -> str:
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
    
    def load_tpch_dataset(
        self,
        dataset_path: Path,
        catalog: str = 'iceberg',
        schema: str = 'tpch',
        storage_location: Optional[str] = None,
        use_partitioning: bool = True,
        dataset_name: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Load TPC-H dataset into Iceberg tables with recommended partitioning.
        
        Args:
            dataset_path: Path to TPC-H Parquet files
            catalog: Trino Iceberg catalog name
            schema: Schema name to create
            storage_location: Optional S3 location
            use_partitioning: Whether to partition large tables (lineitem, orders)
            dataset_name: Dataset name for TPC-H catalog matching (e.g., 'tpch-tiny')
        
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
            partition_specs=partition_specs,
            dataset_name=dataset_name
        )
    
    def _get_connection(self, catalog: str, schema: str):
        """Create Trino connection."""
        return connect(
            host=self.connection_params.host,
            port=self.connection_params.port,
            user=self.connection_params.user,
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
            # Schema might already exist, but if it failed for other reasons (e.g. S3 bucket missing),
            # we should know about it.
            logger.warning(f"Schema creation failed (ignoring if it already exists): {e}")
    
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
        'host': config.get('host', Defaults.Trino.HOST),
        'port': config.get('port', Defaults.Trino.PORT),
        'user': config.get('user', Defaults.Trino.USER)
    }
    
    return IcebergDataLoader(connection_params)
