"""
Dataset management package.

Provides modular dataset management components.
"""

from .schema import BenchmarkType, DatasetSchema, TPCHSchema, TPCDSSchema, SchemaFactory
from .metadata import DatasetMetadata, DatasetValidator
from .generator import TPCHGenerator
from .loader import TrinoDataLoader
from .registry import DatasetRegistry

__all__ = [
    'BenchmarkType',
    'DatasetSchema',
    'TPCHSchema',
    'TPCDSSchema',
    'SchemaFactory',
    'DatasetMetadata',
    'DatasetValidator',
    'TPCHGenerator',
    'TrinoDataLoader',
    'DatasetRegistry',
]
