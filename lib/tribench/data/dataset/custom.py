"""
Custom dataset schema that auto-discovers tables from Parquet files.

This allows loading any custom dataset without requiring registration or
benchmark-specific schema definitions.
"""

import logging
from pathlib import Path
from typing import List
import pyarrow as pa
import pyarrow.parquet as pq

from .schema import DatasetSchema, BenchmarkType

logger = logging.getLogger(__name__)


class CustomDatasetSchema(DatasetSchema):
    """
    Auto-discovering schema for custom datasets.
    
    Automatically detects tables and schemas from Parquet files in a directory.
    No pre-registration or schema definition required.
    """
    
    def __init__(self, dataset_path: Path):
        """
        Initialize custom dataset schema from directory of Parquet files.
        
        Args:
            dataset_path: Path to directory containing .parquet files
        """
        self.dataset_path = Path(dataset_path)
        self._tables = []
        self._schemas = {}
        self._discover_tables()
    
    def _discover_tables(self):
        """Discover all Parquet files in the dataset directory."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset path not found: {self.dataset_path}")
        
        if not self.dataset_path.is_dir():
            raise NotADirectoryError(f"Dataset path is not a directory: {self.dataset_path}")
        
        # Find all .parquet files
        parquet_files = sorted(self.dataset_path.glob("*.parquet"))
        
        if not parquet_files:
            raise ValueError(f"No .parquet files found in: {self.dataset_path}")
        
        logger.info(f"Discovered {len(parquet_files)} Parquet files in {self.dataset_path}")
        
        # Extract table names and read schemas
        for parquet_file in parquet_files:
            table_name = parquet_file.stem  # filename without extension
            
            try:
                # Read schema from Parquet file
                parquet_table = pq.read_table(parquet_file, memory_map=True)
                arrow_schema = parquet_table.schema
                
                self._tables.append(table_name)
                self._schemas[table_name] = arrow_schema
                
                logger.debug(f"  Discovered table: {table_name} ({len(arrow_schema)} columns, {len(parquet_table):,} rows)")
                
            except Exception as e:
                logger.warning(f"  Failed to read {parquet_file.name}: {e}")
                continue
        
        if not self._tables:
            raise ValueError(f"Could not read any valid Parquet files from: {self.dataset_path}")
        
        logger.info(f"Successfully discovered {len(self._tables)} tables: {', '.join(self._tables)}")
    
    def get_benchmark_type(self) -> BenchmarkType:
        """Return generic 'custom' benchmark type."""
        # Return TPCH as default to make it work with existing infrastructure
        # The actual type doesn't matter for custom datasets
        return BenchmarkType.TPCH
    
    def get_tables(self) -> List[str]:
        """Return list of discovered table names."""
        return self._tables
    
    def get_schema(self, table_name: str) -> pa.Schema:
        """
        Return PyArrow schema for a table, read from its Parquet file.
        
        Args:
            table_name: Name of the table
            
        Returns:
            PyArrow schema
            
        Raises:
            KeyError: If table_name was not discovered
        """
        if table_name not in self._schemas:
            raise KeyError(
                f"Table '{table_name}' not found. "
                f"Available tables: {', '.join(self._tables)}"
            )
        
        return self._schemas[table_name]
    
    def get_dataset_info(self) -> dict:
        """Get summary information about the discovered dataset."""
        info = {
            'path': str(self.dataset_path),
            'num_tables': len(self._tables),
            'tables': {}
        }
        
        for table_name in self._tables:
            schema = self._schemas[table_name]
            parquet_file = self.dataset_path / f"{table_name}.parquet"
            
            # Get row count
            try:
                parquet_table = pq.read_table(parquet_file, memory_map=True)
                row_count = len(parquet_table)
            except:
                row_count = None
            
            info['tables'][table_name] = {
                'columns': len(schema),
                'column_names': schema.names,
                'rows': row_count,
                'file_size_mb': parquet_file.stat().st_size / (1024 * 1024)
            }
        
        return info
