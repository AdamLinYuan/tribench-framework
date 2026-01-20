#!/usr/bin/env python3
"""
Database migration: Add advanced query metrics to QueryExecution table.

This migration adds high and medium priority metrics for dissertation analysis:
- HIGH: planning_time_ms, analysis_time_ms, spilled_bytes (already exist/being populated)
- HIGH: execution_time_ms (already exists)
- MEDIUM: total_splits, completed_splits, total_tasks, query_plan_hash

Run this script to add new columns to existing databases.

Usage:
    python utils/migrations/001_add_advanced_query_metrics.py
    
Or with custom database:
    TRIBENCH_DATABASE_URL=postgresql://... python utils/migrations/001_add_advanced_query_metrics.py
"""

import sys
import logging
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from sqlalchemy import inspect, BigInteger, Integer, String
from tribench.storage.connection import get_engine, init_database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_column_if_not_exists(engine, table_name: str, column_name: str, column_type: str, nullable: bool = True):
    """Add a column to a table if it doesn't exist."""
    if column_exists(engine, table_name, column_name):
        logger.info(f"Column {table_name}.{column_name} already exists, skipping")
        return
    
    # Determine SQL syntax based on database type
    db_type = engine.dialect.name
    
    if db_type == 'sqlite':
        # SQLite uses ADD COLUMN
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
    elif db_type == 'postgresql':
        # PostgreSQL uses ADD COLUMN
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
    else:
        logger.error(f"Unsupported database type: {db_type}")
        return
    
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        logger.info(f"Added column {table_name}.{column_name} ({column_type})")
    except Exception as e:
        logger.error(f"Failed to add column {table_name}.{column_name}: {e}")


def migrate():
    """Run the migration."""
    logger.info("Starting migration: Add advanced query metrics")
    
    # Initialize database connection
    init_database()
    engine = get_engine()
    
    # Check if table exists
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if 'query_executions' not in tables:
        logger.error("Table query_executions does not exist. Please run init_database first.")
        return False
    
    logger.info("Adding new columns to query_executions table...")
    
    # HIGH PRIORITY: Spill metrics (memory pressure analysis)
    # Note: planning_time_ms, analysis_time_ms, execution_time_ms already exist in schema
    add_column_if_not_exists(engine, 'query_executions', 'spilled_bytes', 'BIGINT', nullable=True)
    
    # MEDIUM PRIORITY: Parallelism metrics
    add_column_if_not_exists(engine, 'query_executions', 'total_splits', 'INTEGER', nullable=True)
    add_column_if_not_exists(engine, 'query_executions', 'completed_splits', 'INTEGER', nullable=True)
    add_column_if_not_exists(engine, 'query_executions', 'total_tasks', 'INTEGER', nullable=True)
    
    # MEDIUM PRIORITY: Query plan hash for plan regression detection
    add_column_if_not_exists(engine, 'query_executions', 'query_plan_hash', 'VARCHAR(64)', nullable=True)
    
    logger.info("Migration completed successfully!")
    return True


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
