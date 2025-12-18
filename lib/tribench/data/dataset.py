"""
Dataset management module for TriBench framework.

This module provides classes for:
- Generating benchmark datasets (TPC-H)
- Loading datasets into systems (Trino)
- Validating dataset integrity
- Managing dataset registry and metadata
"""

import json
import hashlib
import subprocess
from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as csv
import yaml

from ..defaults import Defaults
from ..config import ConnectionConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Schema Abstraction Layer
# ============================================================================

class BenchmarkType(Enum):
    """Supported benchmark types."""
    TPCH = "tpch"
    TPCDS = "tpcds"


class DatasetSchema(ABC):
    """
    Abstract base class for dataset schemas.
    
    This provides a polymorphic interface for different benchmark types
    (TPC-H, TPC-DS, etc.) to define their table structures without hardcoding.
    """
    
    @abstractmethod
    def get_benchmark_type(self) -> BenchmarkType:
        """Return the benchmark type this schema represents."""
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """Return list of table names in this benchmark."""
        pass
    
    @abstractmethod
    def get_schema(self, table_name: str) -> pa.Schema:
        """
        Return PyArrow schema for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            PyArrow schema defining columns and types
            
        Raises:
            KeyError: If table_name is not valid for this benchmark
        """
        pass


class TPCHSchema(DatasetSchema):
    """TPC-H benchmark schema definitions."""
    
    def get_benchmark_type(self) -> BenchmarkType:
        return BenchmarkType.TPCH
    
    def get_tables(self) -> List[str]:
        return [
            'nation', 'region', 'customer', 'supplier',
            'part', 'partsupp', 'orders', 'lineitem'
        ]
    
    def get_schema(self, table_name: str) -> pa.Schema:
        """Get PyArrow schema for TPC-H tables."""
        schemas = {
            'nation': pa.schema([
                ('n_nationkey', pa.int32()),
                ('n_name', pa.string()),
                ('n_regionkey', pa.int32()),
                ('n_comment', pa.string())
            ]),
            'region': pa.schema([
                ('r_regionkey', pa.int32()),
                ('r_name', pa.string()),
                ('r_comment', pa.string())
            ]),
            'customer': pa.schema([
                ('c_custkey', pa.int32()),
                ('c_name', pa.string()),
                ('c_address', pa.string()),
                ('c_nationkey', pa.int32()),
                ('c_phone', pa.string()),
                ('c_acctbal', pa.decimal128(15, 2)),
                ('c_mktsegment', pa.string()),
                ('c_comment', pa.string())
            ]),
            'supplier': pa.schema([
                ('s_suppkey', pa.int32()),
                ('s_name', pa.string()),
                ('s_address', pa.string()),
                ('s_nationkey', pa.int32()),
                ('s_phone', pa.string()),
                ('s_acctbal', pa.decimal128(15, 2)),
                ('s_comment', pa.string())
            ]),
            'part': pa.schema([
                ('p_partkey', pa.int32()),
                ('p_name', pa.string()),
                ('p_mfgr', pa.string()),
                ('p_brand', pa.string()),
                ('p_type', pa.string()),
                ('p_size', pa.int32()),
                ('p_container', pa.string()),
                ('p_retailprice', pa.decimal128(15, 2)),
                ('p_comment', pa.string())
            ]),
            'partsupp': pa.schema([
                ('ps_partkey', pa.int32()),
                ('ps_suppkey', pa.int32()),
                ('ps_availqty', pa.int32()),
                ('ps_supplycost', pa.decimal128(15, 2)),
                ('ps_comment', pa.string())
            ]),
            'orders': pa.schema([
                ('o_orderkey', pa.int32()),
                ('o_custkey', pa.int32()),
                ('o_orderstatus', pa.string()),
                ('o_totalprice', pa.decimal128(15, 2)),
                ('o_orderdate', pa.date32()),
                ('o_orderpriority', pa.string()),
                ('o_clerk', pa.string()),
                ('o_shippriority', pa.int32()),
                ('o_comment', pa.string())
            ]),
            'lineitem': pa.schema([
                ('l_orderkey', pa.int32()),
                ('l_partkey', pa.int32()),
                ('l_suppkey', pa.int32()),
                ('l_linenumber', pa.int32()),
                ('l_quantity', pa.decimal128(15, 2)),
                ('l_extendedprice', pa.decimal128(15, 2)),
                ('l_discount', pa.decimal128(15, 2)),
                ('l_tax', pa.decimal128(15, 2)),
                ('l_returnflag', pa.string()),
                ('l_linestatus', pa.string()),
                ('l_shipdate', pa.date32()),
                ('l_commitdate', pa.date32()),
                ('l_receiptdate', pa.date32()),
                ('l_shipinstruct', pa.string()),
                ('l_shipmode', pa.string()),
                ('l_comment', pa.string())
            ])
        }
        
        if table_name not in schemas:
            raise KeyError(f"Unknown TPC-H table: {table_name}")
        
        return schemas[table_name]


class TPCDSSchema(DatasetSchema):
    """
    TPC-DS benchmark schema definitions (stub for future implementation).
    
    TPC-DS is a decision support benchmark with 24 tables.
    This is a placeholder for future TPC-DS support.
    """
    
    def get_benchmark_type(self) -> BenchmarkType:
        return BenchmarkType.TPCDS
    
    def get_tables(self) -> List[str]:
        # TPC-DS has 24 tables - these are the main fact tables
        return [
            'store_sales', 'store_returns', 'catalog_sales', 'catalog_returns',
            'web_sales', 'web_returns', 'inventory',
            'store', 'call_center', 'catalog_page', 'web_site', 'web_page',
            'warehouse', 'customer', 'customer_address', 'customer_demographics',
            'date_dim', 'household_demographics', 'item', 'income_band',
            'promotion', 'reason', 'ship_mode', 'time_dim'
        ]
    
    def get_schema(self, table_name: str) -> pa.Schema:
        """
        Get PyArrow schema for TPC-DS tables.
        
        Note: This is a stub implementation. Full TPC-DS schemas need to be added
        when TPC-DS support is implemented.
        """
        # TODO: Implement full TPC-DS schemas when adding TPC-DS support
        raise NotImplementedError(
            "TPC-DS schema definitions not yet implemented. "
            "This is a placeholder for future TPC-DS support."
        )


class SchemaFactory:
    """
    Factory for creating dataset schema instances.
    
    This provides a centralized way to instantiate the correct schema
    implementation based on the benchmark type.
    """
    
    _SCHEMAS: Dict[BenchmarkType, type[DatasetSchema]] = {
        BenchmarkType.TPCH: TPCHSchema,
        BenchmarkType.TPCDS: TPCDSSchema,
    }
    
    @classmethod
    def create(cls, benchmark_type: BenchmarkType) -> DatasetSchema:
        """
        Create a schema instance for the given benchmark type.
        
        Args:
            benchmark_type: The type of benchmark
            
        Returns:
            DatasetSchema instance for the benchmark
            
        Raises:
            ValueError: If benchmark_type is not supported
        """
        if benchmark_type not in cls._SCHEMAS:
            raise ValueError(
                f"Unsupported benchmark type: {benchmark_type}. "
                f"Supported types: {list(cls._SCHEMAS.keys())}"
            )
        
        schema_class = cls._SCHEMAS[benchmark_type]
        return schema_class()
    
    @classmethod
    def register(cls, benchmark_type: BenchmarkType, 
                 schema_class: type[DatasetSchema]) -> None:
        """
        Register a new schema type (for extensibility).
        
        Args:
            benchmark_type: The benchmark type identifier
            schema_class: The DatasetSchema implementation class
        """
        cls._SCHEMAS[benchmark_type] = schema_class
        logger.info(f"Registered schema for benchmark type: {benchmark_type.value}")


# ============================================================================
# Dataset Metadata and Registry
# ============================================================================


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


class TPCHGenerator:
    """Generates TPC-H datasets using Docker-based dbgen."""
    
    DBGEN_IMAGE = "scalytics/tpch:latest"
    
    def __init__(self, output_dir: Path, config: Optional[Dict] = None):
        """
        Initialize TPC-H generator.
        
        Args:
            output_dir: Directory to store generated datasets
            config: Optional configuration dictionary
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}
        self.schema = TPCHSchema()  # Use schema abstraction
    
    def generate(self, scale_factor: float = 1.0, format: str = 'parquet') -> Path:
        """
        Generate TPC-H dataset at specified scale factor.
        
        Args:
            scale_factor: TPC-H scale factor (1 = 1GB)
            format: Output format ('csv' or 'parquet')
            
        Returns:
            Path to generated dataset directory
        """
        sf_str = str(scale_factor).replace('.', '_')
        dataset_name = f"tpch-sf{sf_str}"
        dataset_path = self.output_dir / dataset_name
        dataset_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating TPC-H dataset: {dataset_name}")
        
        # Generate CSV files using dbgen Docker container
        csv_path = dataset_path / "csv"
        csv_path.mkdir(exist_ok=True)
        
        self._run_dbgen(scale_factor, csv_path)
        
        # Convert to Parquet if requested
        if format == 'parquet':
            logger.info("Converting CSV to Parquet...")
            parquet_path = dataset_path / "parquet"
            parquet_path.mkdir(exist_ok=True)
            self._convert_to_parquet(csv_path, parquet_path)
            return parquet_path
        
        return csv_path
    
    def _run_dbgen(self, scale_factor: float, output_dir: Path) -> None:
        """Run dbgen in Docker container to generate CSV files."""
        try:
            # Check if Docker is available
            subprocess.run(['docker', '--version'], 
                         check=True, 
                         capture_output=True)
            
            # Run dbgen container
            cmd = [
                'docker', 'run', '--rm',
                '-v', f'{output_dir.absolute()}:/data',
                self.DBGEN_IMAGE,
                '-s', str(scale_factor)
            ]
            
            logger.info(f"Running dbgen: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if result.stdout:
                logger.debug(f"dbgen output: {result.stdout}")
            
            logger.info(f"Successfully generated TPC-H SF{scale_factor} data")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run dbgen: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise RuntimeError(f"Failed to generate TPC-H data: {e}")
        except FileNotFoundError:
            raise RuntimeError("Docker is not available. Please install Docker to generate datasets.")
    
    def _convert_to_parquet(self, csv_dir: Path, parquet_dir: Path) -> None:
        """Convert CSV files to Parquet format."""
        for csv_file in csv_dir.glob("*.tbl"):
            table_name = csv_file.stem
            
            if table_name not in self.schema.get_tables():
                logger.warning(f"Unknown table: {table_name}, skipping")
                continue
            
            logger.info(f"Converting {table_name}.tbl to Parquet...")
            
            try:
                # Get schema for this table
                table_schema = self.schema.get_schema(table_name)
                
                # Read CSV with pipe delimiter (TPC-H format)
                # TPC-H .tbl files don't have headers, so we need to specify column names
                # TPC-H files have trailing delimiter creating an extra empty column
                # We add a dummy column name and remove it after reading
                column_names = [field.name for field in table_schema] + ['_dummy']
                
                read_options = csv.ReadOptions(
                    autogenerate_column_names=False,
                    column_names=column_names
                )
                table = csv.read_csv(
                    csv_file,
                    read_options=read_options,
                    parse_options=csv.ParseOptions(
                        delimiter='|',
                        ignore_empty_lines=True
                    ),
                    convert_options=csv.ConvertOptions(
                        column_types=table_schema,
                        strings_can_be_null=True
                    )
                )
                
                # Remove the dummy column created by trailing delimiter
                table = table.drop(['_dummy'])
                
                # Write Parquet file
                parquet_file = parquet_dir / f"{table_name}.parquet"
                pq.write_table(table, parquet_file, compression='snappy')
                
                logger.info(f"Created {parquet_file.name} ({table.num_rows} rows)")
                
            except Exception as e:
                logger.error(f"Failed to convert {table_name}: {e}")
                raise


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


class DatasetRegistry:
    """Registry for tracking available datasets and their metadata."""
    
    def __init__(self, registry_path: Path):
        """
        Initialize dataset registry.
        
        Args:
            registry_path: Path to registry file (YAML)
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._datasets: Dict[str, DatasetMetadata] = {}
        self._load()
    
    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                self._datasets = {
                    name: DatasetMetadata.from_dict(meta)
                    for name, meta in data.items()
                }
            logger.info(f"Loaded {len(self._datasets)} datasets from registry")
    
    def _save(self) -> None:
        """Save registry to disk."""
        data = {
            name: meta.to_dict()
            for name, meta in self._datasets.items()
        }
        with open(self.registry_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved {len(self._datasets)} datasets to registry")
    
    def register(self, metadata: DatasetMetadata) -> None:
        """Register a new dataset."""
        self._datasets[metadata.name] = metadata
        self._save()
        logger.info(f"Registered dataset: {metadata.name}")
    
    def get(self, name: str) -> Optional[DatasetMetadata]:
        """Get dataset metadata by name."""
        return self._datasets.get(name)
    
    def list(self) -> List[DatasetMetadata]:
        """List all registered datasets."""
        return list(self._datasets.values())
    
    def delete(self, name: str) -> bool:
        """Remove dataset from registry."""
        if name in self._datasets:
            del self._datasets[name]
            self._save()
            logger.info(f"Deleted dataset from registry: {name}")
            return True
        return False
    
    def update(self, name: str, metadata: DatasetMetadata) -> None:
        """Update dataset metadata."""
        self._datasets[name] = metadata
        self._save()
        logger.info(f"Updated dataset: {name}")
