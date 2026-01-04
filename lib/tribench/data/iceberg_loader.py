"""
DEPRECATED: This module has been restructured.

The Iceberg data loader implementation has been split into focused modules
in the `tribench.data.iceberg` package for better maintainability.

This file now serves as a backwards-compatibility wrapper and will be
removed in a future version.

Please update imports:
    from tribench.data.iceberg_loader import IcebergDataLoader
to:
    from tribench.data.iceberg import IcebergDataLoader
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "tribench.data.iceberg_loader is deprecated. "
    "Use tribench.data.iceberg instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from new location
from tribench.data.iceberg.loader import IcebergDataLoader, create_iceberg_loader

__all__ = ['IcebergDataLoader', 'create_iceberg_loader']
