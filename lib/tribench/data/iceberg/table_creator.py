"""
Iceberg table creation.

Handles creating Iceberg tables with proper schema and properties.
"""

import logging
from typing import List, Optional

import pyarrow as pa

logger = logging.getLogger(__name__)


class IcebergTableCreator:
    """Creates Iceberg tables with specified schema and properties."""
    
    @staticmethod
    def create_schema(cursor, schema: str, storage_location: Optional[str] = None):
        """
        Create schema if it doesn't exist.
        
        Args:
            cursor: Database cursor
            schema: Schema name
            storage_location: Optional S3 storage location
        """
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
    
    @staticmethod
    def create_table(
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
            sql_type = IcebergTableCreator._arrow_to_trino_type(field.type)
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
    
    @staticmethod
    def _arrow_to_trino_type(arrow_type: pa.DataType) -> str:
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
