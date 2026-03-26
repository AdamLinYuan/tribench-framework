"""Data loading commands."""

import click
from pathlib import Path
from datetime import datetime
import logging

from tribench.cli.base import dry_run_option, verbose_option, config_option, should_use_kubernetes, ensure_k8s_port_forwarding, auto_ensure_trino_connection
from tribench.data.dataset import DatasetRegistry, DatasetMetadata, BenchmarkType, SchemaFactory
from tribench.data.iceberg.universal_loader import UniversalIcebergLoader
from .utils import get_datasets_root, get_all_datasets_roots, get_trino_connection_params

logger = logging.getLogger(__name__)


@click.command(name="load")
@click.argument("dataset")
@click.option('--system', 
              type=click.Choice(['trino']),
              default='trino',
              help='Target system to load data into.')
@click.option('--catalog', default='iceberg', help='Trino catalog name (iceberg, memory, etc.).')
@click.option('--schema', default='tpch', help='Schema/database name.')
@click.option('--storage', help='S3 storage location for Iceberg (e.g., s3://warehouse/tpch/).')
@click.option('--partition/--no-partition', default=True, 
              help='Partition large tables by date (Iceberg only).')
@click.option('--validate', is_flag=True, help='Validate data after loading.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def load(ctx, dataset, system, catalog, schema, storage, partition, validate, config, dry_run, verbose):
    """Load a dataset into a system.

    Uses universal Hive CTAS loading for Iceberg catalog. Works for any benchmark
    (TPC-H, TPC-DS, custom datasets) with fast streaming performance via:
      1. Upload Parquet to MinIO
      2. Create Hive external table (staging)
      3. CTAS from Hive → Iceberg (fast streaming copy)

    Backend selection (Docker/Kubernetes) is configured in host config files.
    Use 'tribench config profile <name>' to set your preferred backend.

    \b
    Examples:
        tribench data load tpch-tiny
        tribench data load tpch-sf1 --no-partition
        tribench data load tpch-sf1 --storage s3://warehouse/tpch/ --validate
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration
    from tribench.utils.config import ConfigurationLoader
    bundle_root = getattr(ctx.obj, 'bundle_root', None)
    config_loader = ConfigurationLoader(bundle_root=bundle_root)
    full_config = config_loader.load(experiment_config=config)
    datasets_root = get_datasets_root(config, bundle_root=bundle_root)
    all_datasets_roots = get_all_datasets_roots(config, bundle_root=bundle_root)
    
    # Determine backend
    use_k8s = should_use_kubernetes(full_config)

    # Handle Kubernetes port forwarding
    if use_k8s:
        if not ensure_k8s_port_forwarding(full_config):
            return
    else:
        # Auto-detect and ensure Trino connection
        auto_ensure_trino_connection(full_config)
    
    if ctx.obj.verbose:
        click.echo(f"Dataset: {dataset}")
        click.echo(f"Target system: {system}")
        click.echo(f"Catalog: {catalog}")
        click.echo(f"Schema: {schema}")
        if storage:
            click.echo(f"Storage location: {storage}")
        click.echo(f"Partitioning: {'enabled' if partition else 'disabled'}")
        if validate:
            click.echo("Validation enabled")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would load dataset: {dataset}")
        click.echo(f"[DRY RUN] Into: {system}/{catalog}/{schema}")
        if catalog == 'iceberg':
            click.echo(f"[DRY RUN] Using fast Iceberg CTAS loading")
        return
    
    try:
        # Search all dataset roots in priority order (bundle first, then framework)
        dataset_path = None
        metadata = None
        for root in all_datasets_roots:
            candidate = root / dataset
            if candidate.exists() and candidate.is_dir():
                dataset_path = candidate
                datasets_root = root
                break
            reg = root / "registry.yaml"
            if reg.exists():
                m = DatasetRegistry(reg).get(dataset)
                if m:
                    metadata = m
                    datasets_root = root
                    dataset_path = candidate
                    break

        if dataset_path is None:
            dataset_path = all_datasets_roots[0] / dataset

        is_custom_dataset = dataset_path.exists() and dataset_path.is_dir()

        # Handle case where dataset is not found
        if not metadata and not is_custom_dataset:
            click.secho(f"✗ Dataset '{dataset}' not found", fg='red')
            click.echo(f"\nSearched:")
            for root in all_datasets_roots:
                reg = root / "registry.yaml"
                if reg.exists():
                    click.echo(f"  - Registry: {reg}")
                click.echo(f"  - Directory: {root / dataset}")
            click.echo(f"\nTo add a custom dataset:")
            click.echo(f"  1. Create directory: {all_datasets_roots[0] / dataset}/")
            click.echo(f"  2. Add Parquet files: {all_datasets_roots[0] / dataset}/*.parquet")
            click.echo(f"  3. Run: tribench data load {dataset}")
            return

        registry_path = datasets_root / "registry.yaml"
        
        # Handle custom dataset (auto-discovery)
        if is_custom_dataset and not metadata:
            click.echo(f"Auto-discovering custom dataset: {dataset}")
            click.echo(f"Location: {dataset_path}")
            
            # Import CustomDatasetSchema
            from tribench.data.dataset import CustomDatasetSchema
            
            # Auto-discover tables and schemas from Parquet files
            try:
                dataset_schema = CustomDatasetSchema(dataset_path)
                
                # Show discovered tables
                info = dataset_schema.get_dataset_info()
                click.echo(f"\nDiscovered {info['num_tables']} tables:")
                for table_name, table_info in info['tables'].items():
                    click.echo(f"  • {table_name:<20} {table_info['rows']:>10,} rows, "
                             f"{table_info['columns']:>2} columns, "
                             f"{table_info['file_size_mb']:>6.2f} MB")
                
            except Exception as e:
                click.secho(f"✗ Failed to auto-discover dataset: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
                return
        
        # Handle registered dataset
        else:
            dataset_path = Path(metadata.location)
            if not dataset_path.exists():
                click.secho(f"✗ Dataset location not found: {dataset_path}", fg='red')
                return
            
            if metadata.format != 'parquet':
                click.secho(f"✗ Only Parquet format is currently supported for loading", fg='red')
                return
            
            # Get dataset schema
            benchmark_type = BenchmarkType(metadata.benchmark_type)
            dataset_schema = SchemaFactory.create(benchmark_type)
        
        # Get Trino connection parameters
        connection_params = get_trino_connection_params(config)
        
        # Route to appropriate loader based on catalog
        if catalog == 'iceberg':
            # Use universal CTAS loader (works for ANY dataset)
            loader = UniversalIcebergLoader(connection_params)
            
            # Determine partitioning strategy
            partition_specs = {}
            if partition and metadata:  # Only apply pre-defined partitions for registered datasets
                benchmark_type = BenchmarkType(metadata.benchmark_type)
                if benchmark_type == BenchmarkType.TPCH:
                    partition_specs = {
                        'lineitem': ['l_shipdate'],
                        'orders': ['o_orderdate']
                    }
                elif benchmark_type == BenchmarkType.TPCDS:
                    partition_specs = {
                        'store_sales': ['ss_sold_date_sk'],
                        'catalog_sales': ['cs_sold_date_sk'],
                        'web_sales': ['ws_sold_date_sk'],
                        'store_returns': ['sr_returned_date_sk'],
                        'catalog_returns': ['cr_returned_date_sk'],
                        'web_returns': ['wr_returned_date_sk']
                    }
            
            # Load using universal CTAS (fast for any benchmark)
            row_counts = loader.load_dataset(
                dataset_path=dataset_path,
                dataset_schema=dataset_schema,
                catalog=catalog,
                schema=schema,
                minio_bucket='warehouse',
                partition_specs=partition_specs,
                storage_location=storage
            )
            
            # Collect and register Iceberg metadata
            click.echo("\\nCollecting Iceberg metadata...")
            iceberg_metadata = loader.collect_iceberg_metadata(
                catalog=catalog,
                schema=schema,
                tables=list(row_counts.keys())
            )
            
            # Register Iceberg dataset (only for registered datasets, not custom)
            if metadata:
                iceberg_dataset_name = f"{dataset}-iceberg"
                
                iceberg_dataset_metadata = DatasetMetadata(
                    name=iceberg_dataset_name,
                    benchmark_type=metadata.benchmark_type,
                    type='static',
                    format='iceberg',
                    scale_factor=metadata.scale_factor,
                    size_bytes=None,
                    location=f"{catalog}.{schema}",
                    tables=list(row_counts.keys()),
                    row_counts=row_counts,
                    checksums={},
                    properties={
                        'source_dataset': dataset,
                        'partitioned': partition,
                        'storage_location': storage if storage else 'default'
                    },
                    created_at=datetime.now().isoformat(),
                    generator='iceberg_loader',
                    iceberg_catalog=catalog,
                    iceberg_schema=schema,
                    snapshot_ids=iceberg_metadata.get('snapshot_ids'),
                    snapshot_timestamps=iceberg_metadata.get('snapshot_timestamps'),
                    manifest_counts=iceberg_metadata.get('manifest_counts'),
                    format_version=iceberg_metadata.get('format_version'),
                    storage_location=iceberg_metadata.get('storage_location')
                )
                
                registry = DatasetRegistry(registry_path)
                registry.register(iceberg_dataset_metadata)
                click.secho(f"✓ Registered Iceberg dataset: {iceberg_dataset_name}", fg='green')
            else:
                # Custom dataset - show success message
                click.secho(f"\n✓ Custom dataset loaded successfully!", fg='green')
                click.echo(f"   Access via: {catalog}.{schema}.<table_name>")
            
        else:
            # Use standard Trino loader for other catalogs (memory, hive, etc.)
            from tribench.data.dataset import TrinoDataLoader
            
            try:
                benchmark_type = BenchmarkType(metadata.benchmark_type)
                dataset_schema = SchemaFactory.create(benchmark_type)
            except (ValueError, KeyError) as e:
                click.secho(f"✗ Unsupported benchmark type: {metadata.benchmark_type}", fg='red')
                click.echo(f"  Supported types: {', '.join([bt.value for bt in BenchmarkType])}")
                return
            
            loader = TrinoDataLoader(connection_params)
            row_counts = loader.load_dataset(dataset_path, dataset_schema, catalog, schema)
        
        click.secho(f"✓ Dataset loaded successfully", fg='green')
        
        # Display summary
        click.echo("\nLoaded tables:")
        for table, count in row_counts.items():
            click.echo(f"  - {table}: {count:,} rows")
        
        if validate:
            click.echo("\nValidating loaded data...")
            # TODO: Implement validation by querying Trino
            click.secho("Note: Load validation not fully implemented yet", fg='yellow')
            
    except Exception as e:
        click.secho(f"✗ Failed to load dataset: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()


@click.command(name="load-iceberg", deprecated=True, hidden=True)
@click.argument("dataset")
@click.option('--catalog', default='iceberg', help='Iceberg catalog name.')
@click.option('--schema', default='tpch', help='Schema/database name.')
@click.option('--storage', help='S3 storage location (e.g., s3://warehouse/tpch/).')
@click.option('--partition/--no-partition', default=True, 
              help='Partition large tables (lineitem, orders) by date.')
@click.option('--validate', is_flag=True, help='Validate data after loading.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def load_iceberg(ctx, dataset, catalog, schema, storage, partition, validate, config, dry_run, verbose):
    """[DEPRECATED] Use 'tribench data load' instead.
    
    This command is deprecated. Please use:
        tribench data load DATASET --catalog iceberg [OPTIONS]
    """
    click.secho("⚠ DEPRECATED: 'load-iceberg' is deprecated. Use 'tribench data load' instead.", fg='yellow')
    click.echo("  Example: tribench data load tpch-tiny --catalog iceberg\n")
    
    # Forward to the new load command
    ctx.invoke(load, 
               dataset=dataset, 
               system='trino',
               catalog=catalog, 
               schema=schema, 
               storage=storage,
               partition=partition,
               validate=validate, 
               config=config, 
               dry_run=dry_run, 
               verbose=verbose)
