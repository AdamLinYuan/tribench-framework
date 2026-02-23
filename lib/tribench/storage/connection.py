"""
Database connection management for result storage.

Provides connection pooling, session management, and database initialization.
"""

import logging
import os
from contextlib import contextmanager
from typing import Optional, Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base
from ..defaults import Defaults

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_SessionFactory = None

# Optional override — set this before init_database() to point at a specific path
# (e.g. a bundle's results directory)
_db_url_override: Optional[str] = None


def set_db_url(url: str) -> None:
    """
    Override the database URL used by all subsequent init_database() calls.

    Call this before any storage operations to redirect to a bundle-specific
    database (e.g. ``sqlite:///bundles/my-bundle/results/tribench.db``).

    If the engine is already initialised for a *different* URL, it is closed
    and will be re-opened on the next operation.
    """
    global _db_url_override, _engine, _SessionFactory
    if url == _db_url_override:
        return  # No change needed
    _db_url_override = url
    # Reset so the next get_db_session() re-initialises with the new URL
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _SessionFactory = None
    logger.debug(f"Database URL override set to: {url}")


def clear_db_url() -> None:
    """Clear the URL override and revert to environment / default discovery."""
    global _db_url_override, _engine, _SessionFactory
    if _db_url_override is None:
        return
    _db_url_override = None
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _SessionFactory = None
    logger.debug("Database URL override cleared")


def get_database_url(config: Optional[dict] = None) -> str:
    """
    Get database URL from configuration or environment.
    
    Priority:
    1. URL override set via set_db_url() (e.g. from --bundle flag)
    2. Explicit config dict
    3. Environment variables
    4. Default SQLite database (results/tribench.db)
    """
    # Priority 1: explicit override (bundle-aware path set at CLI startup)
    if _db_url_override:
        return _db_url_override

    if config and "database_url" in config:
        return config["database_url"]
    
    # Check environment variables
    db_url = os.getenv("TRIBENCH_DATABASE_URL")
    if db_url:
        return db_url
    
    # PostgreSQL from environment
    db_host = os.getenv("TRIBENCH_DB_HOST", Defaults.PostgreSQL.HOST)
    db_port = os.getenv("TRIBENCH_DB_PORT", str(Defaults.PostgreSQL.PORT))
    db_name = os.getenv("TRIBENCH_DB_NAME", Defaults.PostgreSQL.DATABASE)
    db_user = os.getenv("TRIBENCH_DB_USER", Defaults.PostgreSQL.USER)
    db_pass = os.getenv("TRIBENCH_DB_PASSWORD", Defaults.PostgreSQL.PASSWORD)
    
    # Try PostgreSQL if password is set
    if db_pass != Defaults.PostgreSQL.PASSWORD:
        return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    # Default to SQLite for development
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    sqlite_path = results_dir / "tribench.db"
    logger.info(f"Using SQLite database: {sqlite_path}")
    return f"sqlite:///{sqlite_path}"


def init_database(database_url: Optional[str] = None, config: Optional[dict] = None, echo: bool = False) -> None:
    """
    Initialize database connection and create tables.
    
    Args:
        database_url: Optional database URL (overrides config)
        config: Optional configuration dictionary
        echo: Enable SQL echo for debugging
    """
    global _engine, _SessionFactory
    
    if database_url is None:
        database_url = get_database_url(config)
    
    logger.info(f"Initializing database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    
    # Create engine with appropriate settings
    connect_args = {}
    if database_url.startswith("sqlite"):
        # SQLite-specific settings
        connect_args = {"check_same_thread": False}
        pool_class = None  # SQLite doesn't use connection pooling
    else:
        # PostgreSQL settings
        pool_class = QueuePool
    
    _engine = create_engine(
        database_url,
        echo=echo,
        poolclass=pool_class,
        connect_args=connect_args,
        pool_pre_ping=True,  # Verify connections before using
    )
    
    # SQLite optimizations
    if database_url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
            cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
            cursor.close()
    
    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    
    # Create all tables
    Base.metadata.create_all(_engine)
    logger.info("Database initialized successfully")


def get_engine():
    """Get the global database engine."""
    if _engine is None:
        init_database()
    return _engine


def get_session_factory():
    """Get the global session factory."""
    if _SessionFactory is None:
        init_database()
    return _SessionFactory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Provides automatic commit/rollback and cleanup.
    
    Example:
        with get_db_session() as session:
            experiment = Experiment(name="test")
            session.add(experiment)
            session.commit()
    
    Yields:
        Database session
    """
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def close_database() -> None:
    """Close database connections and cleanup."""
    global _engine, _SessionFactory
    
    if _engine:
        _engine.dispose()
        _engine = None
    
    _SessionFactory = None
    logger.info("Database connections closed")
