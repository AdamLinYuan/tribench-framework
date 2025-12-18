"""
DEPRECATED: This module has been restructured.

The dataset management implementation has been split into focused modules
in the `tribench.data.dataset` package for better maintainability.

This file now serves as a backwards-compatibility wrapper and will be
removed in a future version.

Please update imports:
    from tribench.data.dataset import BenchmarkType, DatasetSchema, ...
(This import path remains the same and will continue to work)
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "tribench.data.dataset module has been restructured. "
    "The current import path still works but the internal structure has changed.",
    DeprecationWarning,
    stacklevel=2
)

# Import from new location
from tribench.data.dataset.schema import (
    BenchmarkType,
    DatasetSchema,
    TPCHSchema,
    TPCDSSchema,
    SchemaFactory
)
from tribench.data.dataset.metadata import DatasetMetadata, DatasetValidator
from tribench.data.dataset.generator import TPCHGenerator
from tribench.data.dataset.loader import TrinoDataLoader
from tribench.data.dataset.registry import DatasetRegistry

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
