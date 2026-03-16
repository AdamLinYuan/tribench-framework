"""
Built-in dataset loader — no local parquet files needed.

TPC-H:   CTAS directly from Trino's built-in tpch connector.
TPC-DS:  DuckDB generates data and writes parquet directly to MinIO via S3,
         then CTAS from a Hive staging table into Iceberg.
"""

import logging
import time
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# --- table definitions -------------------------------------------------------

TPCH_TABLES = [
    "nation", "region", "supplier", "customer", "part",
    "partsupp", "orders", "lineitem",
]

TPCDS_TABLES = [
    "call_center", "catalog_page", "catalog_returns", "catalog_sales",
    "customer", "customer_address", "customer_demographics", "date_dim",
    "household_demographics", "income_band", "inventory", "item",
    "promotion", "reason", "ship_mode", "store", "store_returns",
    "store_sales", "time_dim", "warehouse", "web_page", "web_returns",
    "web_sales", "web_site",
]

# Partition hints for large fact tables
TPCH_PARTITIONS = {
    "lineitem": "l_shipdate",
    "orders":   "o_orderdate",
}

def _duckdb_to_trino_type(dtype: str) -> str:
    """Map a DuckDB type string to a Trino-compatible type string."""
    d = dtype.upper().strip()
    if d.startswith(("DECIMAL", "NUMERIC", "VARCHAR", "CHAR")):
        return d  # pass through with precision/length
    return {
        "INTEGER": "INTEGER", "INT": "INTEGER", "INT4": "INTEGER",
        "BIGINT": "BIGINT", "INT8": "BIGINT",
        "SMALLINT": "SMALLINT", "INT2": "SMALLINT",
        "TINYINT": "TINYINT", "INT1": "TINYINT",
        "DOUBLE": "DOUBLE", "FLOAT8": "DOUBLE",
        "FLOAT": "REAL", "FLOAT4": "REAL",
        "DATE": "DATE",
        "TIMESTAMP": "TIMESTAMP",
        "TIME": "TIME",
        "BOOLEAN": "BOOLEAN", "BOOL": "BOOLEAN",
        "HUGEINT": "DECIMAL(38,0)",
    }.get(d, d)


TPCDS_PARTITIONS = {
    "store_sales":    "ss_sold_date_sk",
    "catalog_sales":  "cs_sold_date_sk",
    "web_sales":      "ws_sold_date_sk",
    "store_returns":  "sr_returned_date_sk",
    "catalog_returns":"cr_returned_date_sk",
    "web_returns":    "wr_returned_date_sk",
    "inventory":      "inv_date_sk",
}

# Trino built-in tpch connector schema names
def _tpch_connector_schema(scale_factor: float) -> str:
    if scale_factor <= 0.01:
        return "tiny"
    sf = int(scale_factor) if scale_factor == int(scale_factor) else scale_factor
    return f"sf{sf}"


# --- helpers -----------------------------------------------------------------

def _trino_execute(conn, sql: str, description: str = ""):
    """Execute a Trino SQL statement and wait for completion."""
    if description:
        logger.info(f"  {description}")
    logger.debug(f"SQL: {sql}")
    cur = conn.cursor()
    cur.execute(sql)
    # consume result to ensure completion
    try:
        cur.fetchall()
    except Exception:
        pass


def _trino_connect(connection_params):
    """Return a trino-python-client connection."""
    import trino
    return trino.dbapi.connect(
        host=connection_params.host,
        port=connection_params.port,
        user=connection_params.user or "tribench",
        http_scheme="http",
    )


# --- TPC-H via Trino built-in connector --------------------------------------

def load_tpch_builtin(
    connection_params,
    schema: str,
    scale_factor: float,
    catalog: str = "iceberg",
    partition: bool = True,
    storage_location: Optional[str] = None,
) -> Dict[str, int]:
    """
    Load TPC-H into Iceberg using Trino's built-in tpch connector.
    Runs entirely inside GKE — no local data touched.
    """
    import click

    src_schema = _tpch_connector_schema(scale_factor)
    row_counts: Dict[str, int] = {}

    conn = _trino_connect(connection_params)

    click.echo(f"  Source: tpch.{src_schema}  →  {catalog}.{schema}")

    # Create target schema
    _trino_execute(
        conn,
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema} "
        f"WITH (location = 's3://warehouse/{schema}/')",
        f"Creating schema {catalog}.{schema}",
    )

    for table in TPCH_TABLES:
        loc = f"s3://warehouse/{schema}/{table}/"
        if storage_location:
            loc = f"{storage_location.rstrip('/')}/{table}/"

        part_col = TPCH_PARTITIONS.get(table) if partition else None
        with_clause = f"location = '{loc}'"
        if part_col:
            with_clause += f", partitioning = ARRAY['month({part_col})']"

        click.echo(f"    → {table} ...", nl=False)
        t0 = time.time()

        _trino_execute(
            conn,
            f"CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table} "
            f"WITH ({with_clause}) "
            f"AS SELECT * FROM tpch.{src_schema}.{table}",
        )

        # Get row count
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {catalog}.{schema}.{table}")
        count = cur.fetchone()[0]
        row_counts[table] = count
        elapsed = time.time() - t0
        click.echo(f" {count:,} rows ({elapsed:.0f}s)")

    return row_counts


# --- TPC-DS via DuckDB → MinIO → Iceberg ------------------------------------

def load_tpcds_duckdb(
    connection_params,
    schema: str,
    scale_factor: float,
    catalog: str = "iceberg",
    partition: bool = True,
    storage_location: Optional[str] = None,
    minio_endpoint: str = "localhost:9000",
    minio_access_key: str = "minioadmin",
    minio_secret_key: str = "minioadmin",
    minio_bucket: str = "warehouse",
) -> Dict[str, int]:
    """
    Load TPC-DS into Iceberg via:
      1. DuckDB generates data + writes parquet directly to MinIO (no local disk).
      2. Trino CTAS from Hive external staging table → Iceberg.
    """
    import click

    try:
        import duckdb
    except ImportError:
        raise RuntimeError(
            "duckdb is required for TPC-DS built-in loading. "
            "Install it with: pip install duckdb"
        )

    sf = int(scale_factor) if scale_factor == int(scale_factor) else scale_factor
    click.echo(f"  Generating TPC-DS SF{sf} via DuckDB → MinIO ({minio_endpoint})")

    # --- Step 1: DuckDB generates and writes to MinIO via S3 -----------------
    duck = duckdb.connect()
    duck.execute("INSTALL tpcds; LOAD tpcds")
    duck.execute("INSTALL httpfs; LOAD httpfs")
    duck.execute(f"""
        SET s3_endpoint='{minio_endpoint}';
        SET s3_access_key_id='{minio_access_key}';
        SET s3_secret_access_key='{minio_secret_key}';
        SET s3_use_ssl=false;
        SET s3_url_style='path';
    """)

    click.echo(f"  Running dsdgen(sf={sf}) — this may take a few minutes ...")
    duck.execute(f"CALL dsdgen(sf={sf})")
    click.echo("  dsdgen complete, exporting tables to MinIO ...")

    # Write parquet to a separate staging prefix so Iceberg table locations are clean
    staging_prefix = f"s3://{minio_bucket}/{schema}_staging"
    table_schemas: Dict[str, str] = {}
    for table in TPCDS_TABLES:
        s3_path = f"{staging_prefix}/{table}/data.parquet"
        click.echo(f"    → exporting {table} ...", nl=False)
        t0 = time.time()
        duck.execute(f"COPY {table} TO '{s3_path}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE true)")
        elapsed = time.time() - t0
        click.echo(f" done ({elapsed:.0f}s)")
        # Collect column DDL from DuckDB while the table is still in memory
        desc = duck.execute(f"DESCRIBE {table}").fetchall()
        table_schemas[table] = ", ".join(
            f'"{row[0]}" {_duckdb_to_trino_type(row[1])}' for row in desc
        )

    duck.close()

    # --- Step 2: Trino CTAS from Hive staging → Iceberg ----------------------
    click.echo(f"  Creating Iceberg tables via Trino CTAS ...")
    conn = _trino_connect(connection_params)

    _trino_execute(
        conn,
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema} "
        f"WITH (location = 's3://{minio_bucket}/{schema}/')",
        f"Creating schema {catalog}.{schema}",
    )

    # Hive staging schema points to the staging S3 prefix (separate from Iceberg)
    _trino_execute(
        conn,
        f"CREATE SCHEMA IF NOT EXISTS hive.{schema}_staging "
        f"WITH (location = 's3://{minio_bucket}/{schema}_staging/')",
        "Creating hive staging schema",
    )

    row_counts: Dict[str, int] = {}

    for table in TPCDS_TABLES:
        s3_table_path = f"s3://{minio_bucket}/{schema}_staging/{table}/"  # parquet location
        loc = f"s3://{minio_bucket}/{schema}/{table}/"  # Iceberg table location
        if storage_location:
            loc = f"{storage_location.rstrip('/')}/{table}/"

        part_col = TPCDS_PARTITIONS.get(table) if partition else None
        with_clause = f"location = '{loc}'"
        if part_col:
            with_clause += f", partitioning = ARRAY['{part_col}']"

        click.echo(f"    → CTAS {table} ...", nl=False)
        t0 = time.time()

        # Create Hive external staging table using DuckDB-derived column definitions
        staging = f"hive.{schema}_staging.{table}_stage"
        _trino_execute(conn, f"DROP TABLE IF EXISTS {staging}")
        _trino_execute(
            conn,
            f"CREATE TABLE {staging} ({table_schemas[table]}) "
            f"WITH (external_location = '{s3_table_path}', format = 'PARQUET')",
        )

        # CTAS from staging into Iceberg
        _trino_execute(
            conn,
            f"CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table} "
            f"WITH ({with_clause}) "
            f"AS SELECT * FROM {staging}",
        )

        # Cleanup staging
        _trino_execute(conn, f"DROP TABLE IF EXISTS {staging}")

        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {catalog}.{schema}.{table}")
        count = cur.fetchone()[0]
        row_counts[table] = count
        elapsed = time.time() - t0
        click.echo(f" {count:,} rows ({elapsed:.0f}s)")

    # Drop staging schema
    _trino_execute(conn, f"DROP SCHEMA IF EXISTS hive.{schema}_staging")

    return row_counts
