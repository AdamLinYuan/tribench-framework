"""
Schema abstraction layer for benchmark datasets.

Provides polymorphic interfaces for different benchmark types (TPC-H, TPC-DS, etc.).
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict

import pyarrow as pa

logger = logging.getLogger(__name__)


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
