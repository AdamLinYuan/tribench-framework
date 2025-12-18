"""
Iceberg table creation and data loading.

Main orchestrator for loading datasets into Iceberg tables in Trino.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from trino.dbapi import connect

from tribench.data.dataset import DatasetSchema, TPCHSchema
from tribench.defaults import Defaults
from tribench.config import ConnectionConfig

from .mappings import get_tpch_scale_factor
from .table_creator import IcebergTableCreator
from .data_loader import IcebergDataLoader as DataLoadingStrategy
from .metadata_collector import IcebergMetadataCollector

logger = logging.getLogger(__name__)


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
        IcebergTableCreator.create_schema(cursor, schema, storage_location)
        
        # Check if we can use fast CTAS loading from tpch catalog
        tpch_sf = None
        if fast_mode and dataset_name:
            tpch_sf = get_tpch_scale_factor(dataset_name)
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
                    row_count = DataLoadingStrategy.load_via_ctas(
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
                    IcebergTableCreator.create_table(
                        cursor,
                        table_name,
                        table_schema,
                        partitioning,
                        storage_location
                    )
                    
                    # Load data from Parquet file
                    row_count = DataLoadingStrategy.load_via_batch_insert(
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
            Dict with Iceberg metadata
        """
        conn = self._get_connection(catalog, schema)
        cursor = conn.cursor()
        
        metadata = IcebergMetadataCollector.collect_metadata(cursor, catalog, schema, tables)
        
        cursor.close()
        conn.close()
        
        return metadata
    
    def _get_connection(self, catalog: str, schema: str):
        """Create Trino connection."""
        return connect(
            host=self.connection_params.host,
            port=self.connection_params.port,
            user=self.connection_params.user,
            catalog=catalog,
            schema=schema
        )
    
    def _check_tpch_catalog(self, cursor) -> bool:
        """Check if Trino's built-in tpch catalog is available."""
        if self._tpch_catalog_available is not None:
            return self._tpch_catalog_available
        
        self._tpch_catalog_available = DataLoadingStrategy.check_tpch_catalog(cursor)
        return self._tpch_catalog_available


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
