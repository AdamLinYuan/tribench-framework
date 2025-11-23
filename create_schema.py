from trino.dbapi import connect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_schema():
    conn = connect(
        host='localhost',
        port=8080,
        user='admin',
        catalog='iceberg',
        schema='default'  # Connect to default schema first
    )
    cursor = conn.cursor()
    
    try:
        logger.info("Creating schema iceberg.tpch...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS iceberg.tpch WITH (location = 's3://warehouse/tpch')")
        logger.info("Schema created successfully.")
        
        # Verify
        cursor.execute("SHOW SCHEMAS FROM iceberg")
        schemas = cursor.fetchall()
        logger.info(f"Schemas in iceberg: {schemas}")
        
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_schema()
