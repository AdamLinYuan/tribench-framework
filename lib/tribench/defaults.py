"""
Centralized default values for the tribench framework.

This module provides a single source of truth for all default configuration
values used throughout the framework. These defaults can be overridden by
configuration files (reference.conf, host configs, experiment configs).

Usage:
    from tribench.defaults import Defaults
    
    host = config.get("trino.host", Defaults.TRINO_HOST)
"""

from dataclasses import dataclass
from typing import Final


# =============================================================================
# Host Defaults
# =============================================================================

class Hosts:
    """Default host addresses."""
    LOCALHOST: Final[str] = "localhost"
    LOCALHOST_IP: Final[str] = "127.0.0.1"


# =============================================================================
# Port Defaults
# =============================================================================

class Ports:
    """Default port numbers for services."""
    TRINO: Final[int] = 8080
    MINIO_API: Final[int] = 9000
    MINIO_CONSOLE: Final[int] = 9001
    POSTGRESQL: Final[int] = 5432
    HIVE_METASTORE: Final[int] = 9083


# =============================================================================
# Credential Defaults
# =============================================================================

class Credentials:
    """Default credentials (for development/testing only)."""
    # MinIO defaults
    MINIO_ACCESS_KEY: Final[str] = "minioadmin"
    MINIO_SECRET_KEY: Final[str] = "minioadmin"
    
    # PostgreSQL defaults
    POSTGRESQL_USER: Final[str] = "tribench"
    POSTGRESQL_PASSWORD: Final[str] = "tribench"
    POSTGRESQL_DATABASE: Final[str] = "tribench"
    
    # Trino defaults
    TRINO_USER: Final[str] = "tribench"
    
    # Hive Metastore defaults (metastore database credentials)
    HIVE_METASTORE_DB_NAME: Final[str] = "metastore"
    HIVE_METASTORE_DB_USER: Final[str] = "hive"
    HIVE_METASTORE_DB_PASSWORD: Final[str] = "hivepassword"


# =============================================================================
# Service Name Defaults
# =============================================================================

class ServiceNames:
    """Default service/container names."""
    # Docker container names
    TRINO: Final[str] = "tribench-trino"
    MINIO: Final[str] = "tribench-minio"
    POSTGRESQL: Final[str] = "tribench-postgresql"
    HIVE_METASTORE: Final[str] = "tribench-hive-metastore"
    
    # Docker network
    NETWORK: Final[str] = "tribench-network"


# =============================================================================
# Kubernetes Defaults
# =============================================================================

class Kubernetes:
    """Default Kubernetes configuration."""
    CONTEXT: Final[str] = "kind-tribench"
    NAMESPACE: Final[str] = "tribench"
    
    # Service names in K8s
    SERVICE_TRINO: Final[str] = "tribench-trino"
    SERVICE_MINIO: Final[str] = "tribench-minio"
    SERVICE_POSTGRESQL: Final[str] = "tribench-postgresql"
    SERVICE_HIVE_METASTORE: Final[str] = "tribench-hive-metastore"


# =============================================================================
# Timeout Defaults (in seconds)
# =============================================================================

class Timeouts:
    """Default timeout values in seconds."""
    # Kubernetes timeouts
    K8S_DEPLOYMENT: Final[int] = 300
    K8S_POD_READY: Final[int] = 120
    K8S_POLL_INTERVAL: Final[int] = 10
    
    # Service timeouts
    TRINO: Final[int] = 120
    MINIO: Final[int] = 60
    POSTGRESQL: Final[int] = 60
    HIVE_METASTORE: Final[int] = 120
    
    # Query execution
    QUERY: Final[int] = 300
    
    # Monitoring
    MONITORING_INTERVAL: Final[float] = 1.0
    MONITORING_TIMEOUT: Final[int] = 5
    
    # Storage
    STORAGE_TIMEOUT: Final[int] = 30
    
    # CLI
    CLI_TIMEOUT: Final[int] = 120
    
    # General
    DEFAULT: Final[int] = 60


# =============================================================================
# Retry/Batch Defaults
# =============================================================================

class Retry:
    """Default retry and batch configuration."""
    # Max retries
    K8S_MAX_RETRIES: Final[int] = 30
    MINIO_MAX_RETRIES: Final[int] = 10
    STORAGE_MAX_RETRIES: Final[int] = 3
    DEFAULT_MAX_RETRIES: Final[int] = 3
    
    # Retry intervals (seconds)
    K8S_POLL_INTERVAL: Final[int] = 10
    MINIO_RETRY_INTERVAL: Final[int] = 2
    DEFAULT_RETRY_INTERVAL: Final[int] = 5
    HEALTH_CHECK_INTERVAL: Final[int] = 5  # Sleep between health checks
    PORT_FORWARD_STARTUP_DELAY: Final[int] = 2  # Delay after starting port forward
    PROCESS_KILL_DELAY: Final[int] = 1  # Delay between SIGTERM and SIGKILL
    
    # Batch sizes
    ANALYSIS_BATCH_SIZE: Final[int] = 1000
    STORAGE_BATCH_SIZE: Final[int] = 1000
    DATA_BATCH_SIZE_SMALL: Final[int] = 1000  # For small tables (<10k rows)
    DATA_BATCH_SIZE_MEDIUM: Final[int] = 2000  # For medium tables (10k-100k rows)
    DATA_BATCH_SIZE_LARGE: Final[int] = 5000  # For large tables (100k-1M rows)
    DATA_BATCH_SIZE_XLARGE: Final[int] = 10000  # For very large tables (>1M rows)


# =============================================================================
# Trino Defaults
# =============================================================================

class Trino:
    """Default Trino configuration."""
    HOST: Final[str] = Hosts.LOCALHOST
    PORT: Final[int] = Ports.TRINO
    USER: Final[str] = Credentials.TRINO_USER
    CATALOG: Final[str] = "memory"
    SCHEMA: Final[str] = "default"


# =============================================================================
# MinIO Defaults
# =============================================================================

class MinIO:
    """Default MinIO configuration."""
    HOST: Final[str] = Hosts.LOCALHOST
    PORT: Final[int] = Ports.MINIO_API
    CONSOLE_PORT: Final[int] = Ports.MINIO_CONSOLE
    ACCESS_KEY: Final[str] = Credentials.MINIO_ACCESS_KEY
    SECRET_KEY: Final[str] = Credentials.MINIO_SECRET_KEY
    TIMEOUT: Final[int] = Timeouts.MINIO
    MAX_RETRIES: Final[int] = Retry.MINIO_MAX_RETRIES
    RETRY_INTERVAL: Final[int] = Retry.MINIO_RETRY_INTERVAL


# =============================================================================
# PostgreSQL Defaults
# =============================================================================

class PostgreSQL:
    """Default PostgreSQL configuration."""
    HOST: Final[str] = Hosts.LOCALHOST
    PORT: Final[int] = Ports.POSTGRESQL
    USER: Final[str] = Credentials.POSTGRESQL_USER
    PASSWORD: Final[str] = Credentials.POSTGRESQL_PASSWORD
    DATABASE: Final[str] = Credentials.POSTGRESQL_DATABASE
    TIMEOUT: Final[int] = Timeouts.POSTGRESQL


# =============================================================================
# Hive Metastore Defaults
# =============================================================================

class HiveMetastore:
    """Default Hive Metastore configuration."""
    HOST: Final[str] = Hosts.LOCALHOST
    PORT: Final[int] = Ports.HIVE_METASTORE
    TIMEOUT: Final[int] = Timeouts.HIVE_METASTORE
    # Metastore database credentials
    DB_NAME: Final[str] = Credentials.HIVE_METASTORE_DB_NAME
    DB_USER: Final[str] = Credentials.HIVE_METASTORE_DB_USER
    DB_PASSWORD: Final[str] = Credentials.HIVE_METASTORE_DB_PASSWORD


# =============================================================================
# Docker Defaults
# =============================================================================

class Docker:
    """Default Docker configuration."""
    NETWORK: Final[str] = ServiceNames.NETWORK


# =============================================================================
# Unified Defaults Class
# =============================================================================

class Defaults:
    """
    Unified access to all default values.
    
    Usage:
        from tribench.defaults import Defaults
        
        # Access via unified class
        host = Defaults.Trino.HOST
        port = Defaults.Trino.PORT
        
        # Or access component classes directly
        from tribench.defaults import Trino, MinIO, Timeouts
        host = Trino.HOST
    """
    # Component classes
    Hosts = Hosts
    Ports = Ports
    Credentials = Credentials
    ServiceNames = ServiceNames
    Kubernetes = Kubernetes
    Timeouts = Timeouts
    Retry = Retry
    Trino = Trino
    MinIO = MinIO
    PostgreSQL = PostgreSQL
    HiveMetastore = HiveMetastore
    Docker = Docker
    
    # Convenience aliases for most common values
    TRINO_HOST: Final[str] = Trino.HOST
    TRINO_PORT: Final[int] = Trino.PORT
    TRINO_USER: Final[str] = Trino.USER
    
    MINIO_HOST: Final[str] = MinIO.HOST
    MINIO_PORT: Final[int] = MinIO.PORT
    
    POSTGRESQL_HOST: Final[str] = PostgreSQL.HOST
    POSTGRESQL_PORT: Final[int] = PostgreSQL.PORT
    
    K8S_CONTEXT: Final[str] = Kubernetes.CONTEXT
    K8S_NAMESPACE: Final[str] = Kubernetes.NAMESPACE
    
    DOCKER_NETWORK: Final[str] = Docker.NETWORK
