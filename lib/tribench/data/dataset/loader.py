"""
Trino data loader.

Handles loading datasets into Trino (benchmark-agnostic).
"""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, Any

import pyarrow as pa
import pyarrow.parquet as pq

from tribench.config import ConnectionConfig
from tribench.defaults import Defaults
from .schema import DatasetSchema, TPCHSchema

logger = logging.getLogger(__name__)


class TrinoDataLoader:
    """Loads datasets into Trino (benchmark-agnostic)."""
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
        """
        Initialize Trino data loader.
        
        Args:
            connection_params: Trino connection parameters (dict) or None to use defaults.
                             Can also accept ConnectionConfig directly.
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
    
    def load_dataset(self, dataset_path: Path, dataset_schema: DatasetSchema,
                    catalog: str = 'memory', schema: str = 'default') -> Dict[str, int]:
        """
        Load dataset into Trino (works with any benchmark type).
        
        Args:
            dataset_path: Path to Parquet files
            dataset_schema: DatasetSchema instance (e.g., TPCHSchema, TPCDSSchema)
            catalog: Trino catalog name
            schema: Schema name to create
            
        Returns:
            Dict mapping table names to row counts
        """
        from trino.dbapi import connect
        
        benchmark_type = dataset_schema.get_benchmark_type().value
        logger.info(f"Loading {benchmark_type.upper()} dataset from {dataset_path}")
        logger.info(f"Target: {catalog}.{schema}")
        
        # Connect to Trino using ConnectionConfig
        conn = connect(
            host=self.connection_params.host,
            port=self.connection_params.port,
            user=self.connection_params.user,
            catalog=catalog,
            schema=schema
        )
        cursor = conn.cursor()
        
        # Create schema if it doesn't exist
        try:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            logger.info(f"Created schema: {schema}")
        except Exception as e:
            logger.warning(f"Schema creation warning: {e}")
        
        row_counts = {}
        
        # Load each table
        for parquet_file in sorted(dataset_path.glob("*.parquet")):
            table_name = parquet_file.stem
            
            logger.info(f"Loading table: {table_name}")
            
            try:
                # Drop table if exists
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # Create table from Parquet file
                # Note: This is a simplified approach for memory connector
                # Real implementation would need to handle file:// URIs
                table = pq.read_table(parquet_file)
                
                # Create table DDL
                create_ddl = self._generate_create_table_ddl(table_name, table.schema)
                cursor.execute(create_ddl)
                
                # Insert data (for memory connector - batch inserts)
                # This is simplified - production would use COPY or external tables
                row_count = self._insert_data(cursor, table_name, table)
                row_counts[table_name] = row_count
                
                logger.info(f"Loaded {table_name}: {row_count} rows")
                
            except Exception as e:
                logger.error(f"Failed to load {table_name}: {e}")
                raise
        
        cursor.close()
        conn.close()
        
        return row_counts
    
    def load_tpch_dataset(self, dataset_path: Path, catalog: str = 'memory',
                         schema: str = 'default') -> Dict[str, int]:
        """
        Load TPC-H dataset into Trino (backward-compatible wrapper).
        
        Deprecated: Use load_dataset() with TPCHSchema() instead.
        This method is kept for backward compatibility.
        
        Args:
            dataset_path: Path to Parquet files
            catalog: Trino catalog name
            schema: Schema name to create
            
        Returns:
            Dict mapping table names to row counts
        """
        logger.warning(
            "load_tpch_dataset() is deprecated. "
            "Use load_dataset(dataset_path, TPCHSchema(), ...) instead."
        )
        return self.load_dataset(dataset_path, TPCHSchema(), catalog, schema)
    
    def _generate_create_table_ddl(self, table_name: str, schema: pa.Schema) -> str:
        """Generate CREATE TABLE DDL from PyArrow schema."""
        columns = []
        
        for field in schema:
            trino_type = self._arrow_to_trino_type(field.type)
            # Quote column names to handle special characters and numeric names
            quoted_name = f'"{field.name}"'
            columns.append(f"{quoted_name} {trino_type}")
        
        columns_str = ",\n  ".join(columns)
        return f"CREATE TABLE {table_name} (\n  {columns_str}\n)"
    
    def _arrow_to_trino_type(self, arrow_type: pa.DataType) -> str:
        """Convert PyArrow type to Trino SQL type."""
        if pa.types.is_int32(arrow_type):
            return "INTEGER"
        elif pa.types.is_int64(arrow_type):
            return "BIGINT"
        elif pa.types.is_string(arrow_type):
            return "VARCHAR"
        elif pa.types.is_decimal(arrow_type):
            return f"DECIMAL({arrow_type.precision}, {arrow_type.scale})"
        elif pa.types.is_date32(arrow_type):
            return "DATE"
        elif pa.types.is_timestamp(arrow_type):
            return "TIMESTAMP"
        else:
            return "VARCHAR"  # Fallback
    
    def _insert_data(self, cursor, table_name: str, table: pa.Table) -> int:
        """Insert data from PyArrow table using batched INSERT statements."""
        num_rows = table.num_rows
        
        if num_rows == 0:
            logger.info(f"No data to insert for {table_name}")
            return 0
        
        # Batch size for INSERT statements
        batch_size = Defaults.Retry.DATA_BATCH_SIZE_SMALL
        column_names = table.schema.names
        quoted_columns = [f'"{col}"' for col in column_names]
        
        # Get schema field types for proper casting
        field_types = {field.name: field.type for field in table.schema}
        
        # Convert PyArrow table to list of rows
        # Use to_pylist() for easier value handling
        rows = table.to_pylist()
        
        inserted = 0
        for i in range(0, num_rows, batch_size):
            batch = rows[i:i + batch_size]
            
            # Build VALUES clause
            values_list = []
            for row in batch:
                # Convert row values to SQL literals with proper types
                values = []
                for col_name in column_names:
                    value = row[col_name]
                    arrow_type = field_types[col_name]
                    values.append(self._format_sql_value(value, arrow_type))
                values_list.append(f"({', '.join(values)})")
            
            # Execute batch INSERT
            insert_sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES {', '.join(values_list)}"
            
            try:
                cursor.execute(insert_sql)
                inserted += len(batch)
                if inserted % 5000 == 0:
                    logger.info(f"  Inserted {inserted}/{num_rows} rows into {table_name}")
            except Exception as e:
                logger.error(f"Failed to insert batch into {table_name}: {e}")
                raise
        
        logger.info(f"Successfully inserted {inserted} rows into {table_name}")
        return inserted
    
    def _format_sql_value(self, value, arrow_type: pa.DataType) -> str:
        """Format a Python value as SQL literal with proper type casting."""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif pa.types.is_string(arrow_type):
            # Cast to VARCHAR to avoid type mismatch with bounded varchar
            escaped = str(value).replace("'", "''")
            return f"CAST('{escaped}' AS VARCHAR)"
        elif pa.types.is_decimal(arrow_type):
            return f"CAST({value} AS DECIMAL({arrow_type.precision}, {arrow_type.scale}))"
        elif pa.types.is_date32(arrow_type):
            return f"DATE '{value}'"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, (date, datetime)):
            return f"DATE '{value}'"
        else:
            # Fallback: convert to string and cast to VARCHAR
            escaped = str(value).replace("'", "''")
            return f"CAST('{escaped}' AS VARCHAR)"
