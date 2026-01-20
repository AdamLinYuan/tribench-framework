"""Data loading commands."""

import click
from pathlib import Path
from datetime import datetime
import logging

from tribench.cli.base import dry_run_option, verbose_option, config_option, kind_option, should_use_kubernetes, ensure_k8s_port_forwarding, auto_ensure_trino_connection
from tribench.data.dataset import DatasetRegistry, DatasetMetadata
from tribench.data.iceberg_loader import IcebergDataLoader
from .utils import get_datasets_root, get_trino_connection_params

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
@kind_option
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def load(ctx, dataset, system, catalog, schema, storage, partition, validate, kind, config, dry_run, verbose):
    """Load a dataset into a system.
    
    Uses fast CTAS loading for Iceberg catalog (recommended).
    Falls back to batch INSERT for other catalogs.
    
    For Kubernetes deployments, use --kind to ensure port forwarding is active.
    
    \b
    Examples:
        tribench data load tpch-tiny --kind
        tribench data load tpch-sf1 --catalog iceberg --kind
        tribench data load tpch-sf1 --catalog memory --schema default
        tribench data load tpch-sf1 --no-partition --kind
        tribench data load tpch-sf1 --storage s3://warehouse/tpch/ --validate
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration
    from tribench.utils.config import ConfigurationLoader
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    datasets_root = get_datasets_root(config)
    
    # Determine backend
    use_k8s = should_use_kubernetes(kind, full_config)
    
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
        # Get dataset metadata
        registry_path = datasets_root / "registry.yaml"
        if not registry_path.exists():
            click.secho(f"✗ Dataset registry not found", fg='red')
            return
        
        registry = DatasetRegistry(registry_path)
        metadata = registry.get(dataset)
        
        if not metadata:
            click.secho(f"✗ Dataset '{dataset}' not found in registry", fg='red')
            return
        
        dataset_path = Path(metadata.location)
        if not dataset_path.exists():
            click.secho(f"✗ Dataset location not found: {dataset_path}", fg='red')
            return
        
        if metadata.format != 'parquet':
            click.secho(f"✗ Only Parquet format is currently supported for loading", fg='red')
            return
        
        click.echo(f"Loading {dataset} into {catalog}.{schema}...")
        
        # Get Trino connection parameters
        connection_params = get_trino_connection_params(config)
        
        # Route to appropriate loader based on catalog
        if catalog == 'iceberg':
            # Use fast Iceberg loader with CTAS
            loader = IcebergDataLoader(connection_params)
            
            if metadata.benchmark_type == 'tpch':
                row_counts = loader.load_tpch_dataset(
                    dataset_path=dataset_path,
                    catalog=catalog,
                    schema=schema,
                    storage_location=storage,
                    use_partitioning=partition,
                    dataset_name=dataset
                )
            else:
                click.secho(f"✗ Benchmark type '{metadata.benchmark_type}' not supported for Iceberg yet", fg='red')
                return
            
            # Collect and register Iceberg metadata
            click.echo("\nCollecting Iceberg metadata...")
            iceberg_metadata = loader.collect_iceberg_metadata(
                catalog=catalog,
                schema=schema,
                tables=list(row_counts.keys())
            )
            
            # Register Iceberg dataset
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
            
            registry.register(iceberg_dataset_metadata)
            click.secho(f"✓ Registered Iceberg dataset: {iceberg_dataset_name}", fg='green')
            
        else:
            # Use standard Trino loader for other catalogs (memory, hive, etc.)
            from tribench.data.dataset import BenchmarkType, SchemaFactory, TrinoDataLoader
            
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
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (ensures port forwarding is active).')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def load_iceberg(ctx, dataset, catalog, schema, storage, partition, validate, kind, config, dry_run, verbose):
    """[DEPRECATED] Use 'tribench data load' instead.
    
    This command is deprecated. Please use:
        tribench data load DATASET --catalog iceberg [OPTIONS]
    """
    click.secho("⚠ DEPRECATED: 'load-iceberg' is deprecated. Use 'tribench data load' instead.", fg='yellow')
    click.echo("  Example: tribench data load tpch-tiny --catalog iceberg --kind\n")
    
    # Forward to the new load command
    ctx.invoke(load, 
               dataset=dataset, 
               system='trino',
               catalog=catalog, 
               schema=schema, 
               storage=storage,
               partition=partition,
               validate=validate, 
               kind=kind, 
               config=config, 
               dry_run=dry_run, 
               verbose=verbose)
