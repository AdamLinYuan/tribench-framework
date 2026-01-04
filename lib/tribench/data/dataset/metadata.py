"""
Dataset metadata and validation.

Provides metadata structures and validation logic for benchmark datasets.
"""

import hashlib
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


@dataclass
class DatasetMetadata:
    """Metadata for a benchmark dataset."""
    
    name: str
    benchmark_type: str  # 'tpch', 'tpcds', etc.
    type: str  # 'static' or 'generated'
    format: str  # 'parquet', 'csv', 'iceberg'
    scale_factor: Optional[float]
    size_bytes: Optional[int]
    location: str
    tables: List[str]
    row_counts: Dict[str, int]
    checksums: Dict[str, str]
    properties: Dict[str, Any]
    created_at: str
    generator: Optional[str] = None
    
    # Iceberg-specific metadata (optional, only for Iceberg format)
    iceberg_catalog: Optional[str] = None
    iceberg_schema: Optional[str] = None
    snapshot_ids: Optional[Dict[str, int]] = None  # table_name -> snapshot_id
    snapshot_timestamps: Optional[Dict[str, str]] = None  # table_name -> timestamp
    manifest_counts: Optional[Dict[str, int]] = None  # table_name -> manifest_count
    format_version: Optional[int] = None  # Iceberg format version (1 or 2)
    storage_location: Optional[str] = None  # file:// or s3:// location
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DatasetMetadata':
        """Create from dictionary."""
        return cls(**data)


class DatasetValidator:
    """Validates dataset integrity and correctness."""
    
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
        }
    }
    
    @staticmethod
    def compute_file_checksum(filepath: Path) -> str:
        """Compute SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def validate_parquet_file(filepath: Path) -> Dict[str, Any]:
        """
        Validate a Parquet file and return metadata.
        
        Returns:
            Dict with 'valid', 'row_count', 'schema', 'size_bytes'
        """
        try:
            table = pq.read_table(filepath)
            return {
                'valid': True,
                'row_count': table.num_rows,
                'schema': str(table.schema),
                'size_bytes': filepath.stat().st_size,
                'checksum': DatasetValidator.compute_file_checksum(filepath)
            }
        except Exception as e:
            logger.error(f"Failed to validate {filepath}: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    @classmethod
    def validate_tpch_dataset(cls, dataset_path: Path, scale_factor: str) -> Dict[str, Any]:
        """
        Validate TPC-H dataset structure and row counts.
        
        Args:
            dataset_path: Path to dataset directory
            scale_factor: Scale factor ('tiny', '1', '10', etc.)
            
        Returns:
            Dict with validation results
        """
        results = {
            'valid': True,
            'tables': {},
            'errors': []
        }
        
        expected_counts = cls.TPCH_ROW_COUNTS.get(scale_factor, {})
        
        for table_name in ['nation', 'region', 'customer', 'supplier', 
                          'part', 'partsupp', 'orders', 'lineitem']:
            parquet_file = dataset_path / f"{table_name}.parquet"
            
            if not parquet_file.exists():
                results['valid'] = False
                results['errors'].append(f"Missing table: {table_name}")
                continue
            
            validation = cls.validate_parquet_file(parquet_file)
            results['tables'][table_name] = validation
            
            if not validation.get('valid'):
                results['valid'] = False
                results['errors'].append(f"Invalid table {table_name}: {validation.get('error')}")
                continue
            
            # Check row count if expected count is known
            if table_name in expected_counts:
                actual_count = validation['row_count']
                expected_count = expected_counts[table_name]
                if actual_count != expected_count:
                    results['valid'] = False
                    results['errors'].append(
                        f"Row count mismatch in {table_name}: "
                        f"expected {expected_count}, got {actual_count}"
                    )
        
        return results
