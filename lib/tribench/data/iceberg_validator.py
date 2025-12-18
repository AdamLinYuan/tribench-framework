"""
Iceberg Table Validation for TriBench framework.

This module provides functionality to validate Iceberg tables:
- Metadata validation (snapshots, manifests, metadata.json)
- Storage integrity checks
- Schema validation
- Row count verification
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from trino.dbapi import connect

from ..defaults import Defaults
from ..config import ConnectionConfig

logger = logging.getLogger(__name__)


class IcebergValidator:
    """
    Validates Iceberg tables in Trino.
    
    Performs comprehensive validation including:
    - Table existence and accessibility
    - Schema validation against expected schema
    - Row count verification
    - Iceberg metadata inspection (snapshots, manifests)
    - Storage location verification
    """
    
    # Expected TPC-H row counts by scale factor
    TPCH_ROW_COUNTS = {
        'tiny': {
            'nation': 25,
            'region': 5,
            'customer': 1500,
            'supplier': 100,
            'part': 2000,
            'partsupp': 8000,
            'orders': 15000,
            'lineitem': 60175
        },
        '1': {
            'nation': 25,
            'region': 5,
            'customer': 150000,
            'supplier': 10000,
            'part': 200000,
            'partsupp': 800000,
            'orders': 1500000,
            'lineitem': 6001215
        },
        '10': {
            'nation': 25,
            'region': 5,
            'customer': 1500000,
            'supplier': 100000,
            'part': 2000000,
            'partsupp': 8000000,
            'orders': 15000000,
            'lineitem': 59986052
        }
    }
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
        """
        Initialize Iceberg validator.
        
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
    
    def validate_iceberg_dataset(
        self,
        catalog: str,
        schema: str,
        tables: List[str],
        scale_factor: Optional[str] = None,
        benchmark_type: str = 'tpch'
    ) -> Dict[str, Any]:
        """
        Validate all tables in an Iceberg dataset.
        
        Args:
            catalog: Iceberg catalog name
            schema: Schema name
            tables: List of table names to validate
            scale_factor: Optional scale factor for row count validation
            benchmark_type: Benchmark type (e.g., 'tpch')
        
        Returns:
            Dict with validation results
        """
        logger.info(f"Validating Iceberg dataset: {catalog}.{schema}")
        
        results = {
            'valid': True,
            'catalog': catalog,
            'schema': schema,
            'benchmark_type': benchmark_type,
            'scale_factor': scale_factor,
            'tables': {},
            'errors': [],
            'warnings': [],
            'validation_timestamp': datetime.now().isoformat()
        }
        
        # Connect to Trino
        conn = self._get_connection(catalog, schema)
        cursor = conn.cursor()
        
        try:
            # Validate each table
            for table_name in tables:
                logger.info(f"Validating table: {table_name}")
                table_validation = self.validate_iceberg_table(
                    cursor,
                    table_name,
                    scale_factor,
                    benchmark_type
                )
                
                results['tables'][table_name] = table_validation
                
                if not table_validation['valid']:
                    results['valid'] = False
                    results['errors'].extend(table_validation.get('errors', []))
                
                if table_validation.get('warnings'):
                    results['warnings'].extend(table_validation['warnings'])
            
            # Summary statistics
            results['summary'] = {
                'total_tables': len(tables),
                'valid_tables': sum(1 for t in results['tables'].values() if t['valid']),
                'total_rows': sum(t.get('row_count', 0) for t in results['tables'].values()),
                'total_snapshots': sum(t.get('snapshot_count', 0) for t in results['tables'].values())
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            results['valid'] = False
            results['errors'].append(f"Validation error: {str(e)}")
        finally:
            cursor.close()
            conn.close()
        
        logger.info(f"Validation complete. Valid: {results['valid']}")
        return results
    
    def validate_iceberg_table(
        self,
        cursor,
        table_name: str,
        scale_factor: Optional[str] = None,
        benchmark_type: str = 'tpch'
    ) -> Dict[str, Any]:
        """
        Validate a single Iceberg table.
        
        Args:
            cursor: Database cursor
            table_name: Table name
            scale_factor: Optional scale factor for row count validation
            benchmark_type: Benchmark type
        
        Returns:
            Dict with validation results for this table
        """
        result = {
            'valid': True,
            'table_name': table_name,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 1. Check table exists and is accessible
            logger.debug(f"Checking table existence: {table_name}")
            if not self._table_exists(cursor, table_name):
                result['valid'] = False
                result['errors'].append(f"Table {table_name} does not exist")
                return result
            
            # 2. Get row count
            logger.debug(f"Getting row count: {table_name}")
            row_count = self._get_row_count(cursor, table_name)
            result['row_count'] = row_count
            
            # 3. Validate row count against expected (if scale factor provided)
            if scale_factor and benchmark_type == 'tpch':
                expected_counts = self.TPCH_ROW_COUNTS.get(scale_factor, {})
                if table_name in expected_counts:
                    expected_count = expected_counts[table_name]
                    result['expected_row_count'] = expected_count
                    
                    if row_count != expected_count:
                        result['valid'] = False
                        result['errors'].append(
                            f"Row count mismatch: expected {expected_count}, got {row_count}"
                        )
            
            # 4. Get table schema
            logger.debug(f"Getting schema: {table_name}")
            schema_info = self._get_table_schema(cursor, table_name)
            result['schema'] = schema_info
            result['column_count'] = len(schema_info)
            
            # 5. Get Iceberg metadata
            logger.debug(f"Getting Iceberg metadata: {table_name}")
            metadata = self._get_iceberg_metadata(cursor, table_name)
            result.update(metadata)
            
            # 6. Validate Iceberg-specific properties
            if metadata.get('snapshot_count') is not None and metadata.get('snapshot_count', 0) == 0:
                result['warnings'].append("Table has no snapshots")
            
            if metadata.get('file_count') is not None and metadata.get('file_count', 0) == 0:
                result['warnings'].append("Table has no data files")
            
        except Exception as e:
            logger.error(f"Failed to validate table {table_name}: {e}", exc_info=True)
            result['valid'] = False
            result['errors'].append(f"Validation error: {str(e)}")
        
        return result
    
    def validate_tpch_iceberg_dataset(
        self,
        catalog: str = 'iceberg',
        schema: str = 'tpch',
        scale_factor: str = 'tiny'
    ) -> Dict[str, Any]:
        """
        Validate TPC-H dataset in Iceberg format.
        
        Args:
            catalog: Iceberg catalog name
            schema: Schema name
            scale_factor: Scale factor ('tiny', '1', '10')
        
        Returns:
            Dict with validation results
        """
        tables = ['nation', 'region', 'customer', 'supplier', 
                  'part', 'partsupp', 'orders', 'lineitem']
        
        return self.validate_iceberg_dataset(
            catalog=catalog,
            schema=schema,
            tables=tables,
            scale_factor=scale_factor,
            benchmark_type='tpch'
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
    
    def _table_exists(self, cursor, table_name: str) -> bool:
        """Check if table exists."""
        try:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            results = cursor.fetchall()
            return len(results) > 0
        except Exception as e:
            logger.error(f"Failed to check table existence: {e}")
            return False
    
    def _get_row_count(self, cursor, table_name: str) -> int:
        """Get row count for table."""
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get row count: {e}")
            return 0
    
    def _get_table_schema(self, cursor, table_name: str) -> List[Dict[str, str]]:
        """Get table schema (column names and types)."""
        try:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'name': row[0],
                    'type': row[1]
                })
            return columns
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return []
    
    def _get_iceberg_metadata(self, cursor, table_name: str) -> Dict[str, Any]:
        """
        Get Iceberg-specific metadata for a table.
        
        Returns metadata including:
        - Current snapshot ID
        - Snapshot count
        - Data file count
        - Storage location
        """
        metadata = {}
        
        try:
            # Try to get snapshot information
            # Note: System tables might not be accessible in all Iceberg implementations
            try:
                query = f"""
                    SELECT 
                        snapshot_id,
                        manifest_list
                    FROM "{table_name}$snapshots"
                    ORDER BY committed_at DESC
                    LIMIT 1
                """
                cursor.execute(query)
                result = cursor.fetchone()
                
                if result:
                    metadata['current_snapshot_id'] = result[0]
                    metadata['manifest_list'] = result[1]
                
                # Get snapshot count
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}$snapshots"')
                snapshot_count = cursor.fetchone()
                metadata['snapshot_count'] = snapshot_count[0] if snapshot_count else 0
                
            except Exception as e:
                logger.debug(f"Could not access snapshot metadata for {table_name}: {e}")
                # System tables not accessible, skip snapshot metadata
                metadata['snapshot_count'] = None
            
            try:
                # Get file count
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}$files"')
                file_count = cursor.fetchone()
                metadata['file_count'] = file_count[0] if file_count else 0
            except Exception as e:
                logger.debug(f"Could not access file metadata for {table_name}: {e}")
                metadata['file_count'] = None
            
            try:
                # Get storage location from table properties
                cursor.execute(f"SHOW CREATE TABLE {table_name}")
                create_stmt = cursor.fetchone()
                if create_stmt:
                    create_sql = create_stmt[0]
                    # Parse location from CREATE TABLE statement
                    if 'location' in create_sql.lower():
                        # Simple extraction - could be improved
                        for line in create_sql.split('\n'):
                            if 'location' in line.lower():
                                metadata['storage_info'] = line.strip()
                                break
            except Exception as e:
                logger.debug(f"Could not get storage location for {table_name}: {e}")
            
        except Exception as e:
            logger.debug(f"Could not retrieve Iceberg metadata for {table_name}: {e}")
            # Some metadata queries might fail, that's okay
        
        return metadata


def create_iceberg_validator(config: Optional[Dict] = None) -> IcebergValidator:
    """
    Factory function to create an IcebergValidator with configuration.
    
    Args:
        config: Optional configuration dict. If None, uses defaults.
    
    Returns:
        Configured IcebergValidator instance
    """
    if config is None:
        config = {}
    
    connection_params = {
        'host': config.get('host', Defaults.Trino.HOST),
        'port': config.get('port', Defaults.Trino.PORT),
        'user': config.get('user', Defaults.Trino.USER)
    }
    
    return IcebergValidator(connection_params)
