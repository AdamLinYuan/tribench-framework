"""
Universal Iceberg Data Loader using CTAS via Hive External Tables.

This loader works for ANY benchmark (TPC-H, TPC-DS, custom datasets) using a clean workflow:
1. Create temporary Hive external table pointing to Parquet files in MinIO
2. Use CTAS from Hive to Iceberg (fast streaming copy)
3. Drop the temporary Hive external table

No benchmark-specific logic needed. No slow batch INSERTs.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

import click
import pyarrow.parquet as pq
from trino.dbapi import connect

from tribench.data.dataset import DatasetSchema
from tribench.config import ConnectionConfig

logger = logging.getLogger(__name__)


class UniversalIcebergLoader:
    """
    Universal Iceberg data loader using Hive external tables for staging.
    
    This is the ONLY loading implementation - fast streaming CTAS that works for any dataset.
    """
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
        """
        Initialize universal loader.
        
        Args:
            connection_params: Trino connection parameters
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
    
    def load_dataset(
        self,
        dataset_path: Path,
        dataset_schema: DatasetSchema,
        catalog: str = 'iceberg',
        schema: str = 'benchmark',
        minio_bucket: str = 'warehouse',
        partition_specs: Optional[Dict[str, List[str]]] = None,
        storage_location: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Load ANY dataset into Iceberg using CTAS via Hive external tables.
        
        Args:
            dataset_path: Path to Parquet files
            dataset_schema: Dataset schema definition
            catalog: Iceberg catalog name (default: 'iceberg')
            schema: Schema name to create (default: 'benchmark')
            minio_bucket: MinIO bucket for data (default: 'warehouse')
            partition_specs: Optional dict mapping table names to partition columns
            storage_location: Optional S3 storage location for Iceberg
        
        Returns:
            Dict mapping table names to row counts
        """
        benchmark_type = dataset_schema.get_benchmark_type().value
        logger.info(f"Universal CTAS loading: {benchmark_type.upper()} dataset")
        logger.info(f"Source: {dataset_path}")
        logger.info(f"Target: {catalog}.{schema}")

        click.echo(f"Loading {benchmark_type.upper()} (from {dataset_path.name}) → {catalog}.{schema}")

        # Connect to Trino
        conn = self._get_connection(catalog, schema)
        cursor = conn.cursor()

        # Create Iceberg schema if needed
        self._create_schema(cursor, catalog, schema, storage_location)

        # Create Hive staging schema if needed
        self._create_staging_schema(cursor)

        partition_specs = partition_specs or {}

        # Collect tables that have parquet files
        tables_to_load = []
        for table_name in dataset_schema.get_tables():
            parquet_file = dataset_path / f"{table_name}.parquet"
            if not parquet_file.exists():
                logger.warning(f"Parquet file not found: {parquet_file}, skipping")
                continue
            tables_to_load.append((table_name, parquet_file))

        # --- Phase 1: Upload Parquet files to MinIO -------------------------
        click.echo(f"  Uploading Parquet files to MinIO...")
        s3_paths: Dict[str, str] = {}
        for table_name, parquet_file in tables_to_load:
            click.echo(f"    \u2192 uploading {table_name} ...", nl=False)
            t0 = time.time()
            s3_path = self._ensure_file_in_minio(parquet_file, minio_bucket, schema, table_name)
            s3_paths[table_name] = s3_path
            click.echo(f" done ({time.time() - t0:.0f}s)")

        # --- Phase 2: CTAS each table into Iceberg --------------------------
        click.echo(f"  Creating Iceberg tables via Trino CTAS ...")
        row_counts: Dict[str, int] = {}
        for table_name, parquet_file in tables_to_load:
            click.echo(f"    \u2192 {table_name} ...", nl=False)
            t0 = time.time()
            try:
                table_schema_def = dataset_schema.get_schema(table_name)
                partitioning = partition_specs.get(table_name)
                timestamp = int(time.time() * 1000)
                staging_table = f"hive.staging.{table_name}_{timestamp}"
                self._create_hive_external_table(
                    cursor=cursor,
                    table_name=staging_table,
                    s3_path=s3_paths[table_name],
                    table_schema=table_schema_def,
                )
                try:
                    iceberg_table = f"{catalog}.{schema}.{table_name}"
                    cursor.execute(f"DROP TABLE IF EXISTS {iceberg_table}")
                    self._ctas_to_iceberg(
                        cursor=cursor,
                        source_table=staging_table,
                        target_table=iceberg_table,
                        partitioning=partitioning,
                        storage_location=storage_location,
                        table_name=table_name,
                    )
                    cursor.execute(f"SELECT COUNT(*) FROM {iceberg_table}")
                    row_count = cursor.fetchone()[0]
                finally:
                    try:
                        cursor.execute(f"DROP TABLE IF EXISTS {staging_table}")
                    except Exception:
                        pass
                row_counts[table_name] = row_count
                click.echo(f" {row_count:,} rows ({time.time() - t0:.0f}s)")
            except Exception as e:
                click.echo(f" FAILED: {e}")
                logger.error(f"Failed to load {table_name}: {e}")
                raise

        cursor.close()
        conn.close()

        return row_counts
    
    def _load_table_via_hive_ctas(
        self,
        cursor,
        table_name: str,
        parquet_file: Path,
        table_schema,
        catalog: str,
        schema: str,
        minio_bucket: str,
        partitioning: Optional[List[str]],
        storage_location: Optional[str]
    ) -> int:
        """
        Load a table using Hive external table + CTAS to Iceberg.
        
        This is fast (streaming copy) and works for any dataset.
        """
        # S3 path in MinIO for Parquet file
        # Upload if not already in MinIO
        s3_path = self._ensure_file_in_minio(parquet_file, minio_bucket, schema, table_name)
        
        # Create temporary Hive external table with unique name (avoid conflicts)
        timestamp = int(time.time() * 1000)
        staging_table = f"hive.staging.{table_name}_{timestamp}"
        self._create_hive_external_table(
            cursor=cursor,
            table_name=staging_table,
            s3_path=s3_path,
            table_schema=table_schema
        )
        
        try:
            # Drop existing Iceberg table if exists
            iceberg_table = f"{catalog}.{schema}.{table_name}"
            cursor.execute(f"DROP TABLE IF EXISTS {iceberg_table}")
            
            # CTAS from Hive to Iceberg (fast streaming copy)
            self._ctas_to_iceberg(
                cursor=cursor,
                source_table=staging_table,
                target_table=iceberg_table,
                partitioning=partitioning,
                storage_location=storage_location,
                table_name=table_name
            )
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {iceberg_table}")
            row_count = cursor.fetchone()[0]
            
            return row_count
            
        finally:
            # Clean up staging table
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {staging_table}")
                logger.debug(f"Dropped staging table: {staging_table}")
            except Exception as e:
                # Permission errors are expected in some environments (e.g., Kubernetes)
                logger.debug(f"Could not drop staging table {staging_table}: {e}")
    
    def _ensure_mc_alias_configured(self) -> bool:
        """
        Ensure mc alias 'local' is configured for MinIO.
        
        Auto-configures if missing. Returns True if configured.
        """
        import subprocess
        
        # Check if 'local' alias exists
        try:
            result = subprocess.run(
                ['mc', 'alias', 'list', 'local'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.debug("mc alias 'local' already configured")
                return True
        except FileNotFoundError:
            logger.error("mc (MinIO client) not found. Install with: brew install minio/stable/mc")
            return False
        except Exception as e:
            logger.debug(f"Failed to check mc alias: {e}")
        
        # Auto-configure 'local' alias
        logger.info("Configuring mc alias 'local' for MinIO...")
        from tribench.defaults import Defaults
        
        try:
            subprocess.run(
                [
                    'mc', 'alias', 'set', 'local',
                    f'http://localhost:{Defaults.MinIO.PORT}',
                    Defaults.MinIO.ACCESS_KEY,
                    Defaults.MinIO.SECRET_KEY
                ],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("✓ mc alias 'local' configured successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure mc alias: {e}")
            logger.error(f"stderr: {e.stderr if e.stderr else 'None'}")
            logger.error("Manual setup: mc alias set local http://localhost:9000 minioadmin minioadmin")
            return False
    
    def _ensure_file_in_minio(self, parquet_file: Path, bucket: str, schema: str, table_name: str) -> str:
        """
        Upload Parquet file to MinIO if needed and return S3 path.
        
        Returns:
            S3 path (e.g., s3://warehouse/tpch/customer/)
        """
        # Ensure mc alias is configured
        if not self._ensure_mc_alias_configured():
            raise RuntimeError("mc client not configured. See logs for setup instructions.")
        
        # For now, use mc to upload (could use boto3 in future)
        import subprocess
        
        # S3 path: s3://bucket/schema/table_name/
        s3_dir = f"s3://{bucket}/{schema}/{table_name}/"
        s3_file = f"{s3_dir}{parquet_file.name}"
        
        # Check if already exists (skip upload if so)
        try:
            result = subprocess.run(
                ['mc', 'stat', f'local/{bucket}/{schema}/{table_name}/{parquet_file.name}'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.debug(f"File already in MinIO: {s3_file}")
                return s3_dir
        except:
            pass
        
        # Upload file
        logger.debug(f"Uploading {parquet_file.name} to MinIO...")
        try:
            subprocess.run(
                ['mc', 'cp', str(parquet_file), f'local/{bucket}/{schema}/{table_name}/'],
                check=True,
                capture_output=True
            )
            logger.debug(f"Uploaded to: {s3_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to upload to MinIO: {e}")
            logger.error(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
            raise RuntimeError(f"Failed to upload {parquet_file} to MinIO")
        
        return s3_dir
    
    def _create_hive_external_table(
        self,
        cursor,
        table_name: str,
        s3_path: str,
        table_schema
    ):
        """Create Hive external table pointing to Parquet files in S3/MinIO."""
        # Try to drop if exists (ignore permission errors)
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        except Exception as e:
            # Ignore permission errors or if table doesn't exist
            logger.debug(f"Could not drop staging table {table_name}: {e}")
        
        # Build column definitions from PyArrow schema
        columns = []
        for field in table_schema:
            # Map PyArrow types to Trino SQL types
            trino_type = self._pyarrow_to_trino_type(field.type)
            columns.append(f"{field.name} {trino_type}")
        
        columns_sql = ",\n      ".join(columns)
        
        # Create external table
        # Note: Hive doesn't support CREATE OR REPLACE, so we try to drop first
        create_sql = f"""
            CREATE TABLE {table_name} (
              {columns_sql}
            )
            WITH (
              external_location = '{s3_path}',
              format = 'PARQUET'
            )
        """
        
        logger.debug(f"Creating Hive external table:\\n{create_sql}")
        cursor.execute(create_sql)
    
    def _ctas_to_iceberg(
        self,
        cursor,
        source_table: str,
        target_table: str,
        partitioning: Optional[List[str]],
        storage_location: Optional[str],
        table_name: str
    ):
        """CTAS from Hive external table to Iceberg table (fast streaming copy)."""
        # Build WITH clause
        properties = ["format = 'PARQUET'"]
        
        if partitioning:
            partition_cols = ", ".join(f"'{col}'" for col in partitioning)
            properties.append(f"partitioning = ARRAY[{partition_cols}]")
        
        if storage_location:
            table_location = f"{storage_location.rstrip('/')}/{table_name}"
            properties.append(f"location = '{table_location}'")
        
        with_clause = ", ".join(properties)
        
        # CTAS
        ctas_sql = f"""
            CREATE TABLE {target_table}
            WITH ({with_clause})
            AS SELECT * FROM {source_table}
        """
        
        logger.debug(f"CTAS SQL:\\n{ctas_sql}")
        cursor.execute(ctas_sql)
    
    def _pyarrow_to_trino_type(self, pa_type) -> str:
        """Convert PyArrow type to Trino SQL type."""
        import pyarrow as pa
        
        if pa.types.is_int32(pa_type):
            return "INTEGER"
        elif pa.types.is_int64(pa_type):
            return "BIGINT"
        elif pa.types.is_float32(pa_type):
            return "REAL"
        elif pa.types.is_float64(pa_type):
            return "DOUBLE"
        elif pa.types.is_string(pa_type) or pa.types.is_large_string(pa_type):
            return "VARCHAR"
        elif pa.types.is_date32(pa_type) or pa.types.is_date64(pa_type):
            return "DATE"
        elif pa.types.is_timestamp(pa_type):
            return "TIMESTAMP"
        elif pa.types.is_decimal(pa_type):
            # Decimal types need precision and scale
            return f"DECIMAL({pa_type.precision}, {pa_type.scale})"
        else:
            # Default to VARCHAR for unknown types
            logger.warning(f"Unknown PyArrow type: {pa_type}, using VARCHAR")
            return "VARCHAR"
    
    def _create_schema(self, cursor, catalog: str, schema: str, storage_location: Optional[str]):
        """Create Iceberg schema if it doesn't exist."""
        try:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
            logger.debug(f"Created schema: {catalog}.{schema}")
        except Exception as e:
            logger.debug(f"Schema already exists or creation failed: {e}")
    
    def _create_staging_schema(self, cursor):
        """Create Hive staging schema for temporary external tables."""
        try:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS hive.staging")
            logger.debug("Created staging schema: hive.staging")
        except Exception as e:
            logger.debug(f"Staging schema already exists or creation failed: {e}")
    
    def _get_connection(self, catalog: str, schema: str):
        """Get Trino connection."""
        if self._connection is None:
            self._connection = connect(
                host=self.connection_params.host,
                port=self.connection_params.port,
                user=self.connection_params.user,
                catalog=catalog,
                schema=schema
            )
        return self._connection
    
    def collect_iceberg_metadata(self, catalog: str, schema: str, tables: List[str]) -> Dict[str, Any]:
        """
        Collect Iceberg metadata for loaded tables.
        
        Args:
            catalog: Iceberg catalog name
            schema: Schema name
            tables: List of table names
        
        Returns:
            Dict with Iceberg metadata
        """
        conn = self._get_connection(catalog, schema)
        cursor = conn.cursor()
        
        metadata = {}
        for table_name in tables:
            try:
                # Get snapshot info
                cursor.execute(f"""
                    SELECT snapshot_id, committed_at 
                    FROM {catalog}.{schema}."{table_name}$snapshots"
                    ORDER BY committed_at DESC
                    LIMIT 1
                """)
                snapshot = cursor.fetchone()
                
                if snapshot:
                    metadata[table_name] = {
                        'snapshot_id': snapshot[0],
                        'snapshot_timestamp': str(snapshot[1])
                    }
            except Exception as e:
                logger.warning(f"Failed to collect metadata for {table_name}: {e}")
        
        cursor.close()
        return metadata
