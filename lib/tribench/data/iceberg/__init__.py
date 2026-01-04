"""
Iceberg table management package.

Provides modular Iceberg table creation and loading components.
"""

from .loader import IcebergDataLoader, create_iceberg_loader

__all__ = ['IcebergDataLoader', 'create_iceberg_loader']
