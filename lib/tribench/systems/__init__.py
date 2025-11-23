"""
Systems module for TriBench framework.

Provides system management classes for different compute/storage systems.
"""

from tribench.systems.trino import TrinoSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.systems.kubernetes_system import KubernetesSystem

__all__ = ['TrinoSystem', 'PostgreSQLSystem', 'MinIOSystem', 'HiveMetastoreSystem', 'KubernetesSystem']
