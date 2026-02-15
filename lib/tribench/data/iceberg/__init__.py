"""
Iceberg table management package.

Provides universal data loading via Hive CTAS for any benchmark.
"""

from .universal_loader import UniversalIcebergLoader

__all__ = ['UniversalIcebergLoader']
