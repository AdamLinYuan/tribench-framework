"""Dataset management commands."""

import click
from pathlib import Path
from datetime import datetime
import logging

from tribench.cli.base import cli, dry_run_option, verbose_option, config_option, kind_option, ensure_k8s_port_forwarding, auto_ensure_trino_connection
from tribench.data.dataset import (
    TPCHGenerator, 
    TrinoDataLoader, 
    DatasetRegistry,
    DatasetValidator,
    DatasetMetadata
)
from tribench.data.iceberg_loader import IcebergDataLoader
from tribench.data.iceberg_validator import IcebergValidator
from tribench.utils.config import ConfigurationLoader
from tribench.defaults import Defaults
from tribench.config import ConnectionConfig

logger = logging.getLogger(__name__)


@cli.group(name="data")
def data_group():
    """Dataset management commands.
    
    Generate, load and manage benchmark datasets.
    """
    pass


@data_group.command(name="generate")
@click.argument("dataset", type=click.Choice(['tpch-tiny', 'tpch-sf1', 'tpch-sf10', 'tpch-sf100']))
@click.option('--format', 
              type=click.Choice(['parquet', 'csv']),
              default='parquet',
              help='Output format for generated data.')
@click.option('--output', type=click.Path(), help='Output directory.')
@click.option('--overwrite', is_flag=True, help='Overwrite existing data.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def generate(ctx, dataset, format, output, overwrite, config, dry_run, verbose):
    """Generate a dataset.
    
    \b
    Examples:
        tribench data generate tpch-sf1
        tribench data generate tpch-sf1 --format parquet
        tribench data generate tpch-sf10 --output /data/tpch --dry-run
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Parse scale factor from dataset name
    scale_factor_map = {
        'tpch-tiny': 0.01,
        'tpch-sf1': 1.0,
        'tpch-sf10': 10.0,
        'tpch-sf100': 100.0
    }
    scale_factor = scale_factor_map[dataset]
    
    # Load configuration
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    
    # Determine output directory
    if output:
        output_dir = Path(output)
    else:
        datasets_root = Path(full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets"))
        output_dir = datasets_root
    
    if ctx.obj.verbose:
        click.echo(f"Dataset: {dataset} (SF={scale_factor})")
        click.echo(f"Format: {format}")
        click.echo(f"Output: {output_dir}")
        if overwrite:
            click.echo("Overwrite mode enabled")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would generate dataset: {dataset}")
        click.echo(f"[DRY RUN] Format: {format}, Output: {output_dir}")
        return
    
    try:
        # Check if dataset exists
        dataset_path = output_dir / f"tpch-sf{str(scale_factor).replace('.', '_')}" / format
        if dataset_path.exists() and not overwrite:
            click.secho(f"✗ Dataset already exists at {dataset_path}", fg='red')
            click.echo("Use --overwrite to regenerate")
            return
        
        click.echo(f"Generating {dataset}...")
        
        # Generate dataset
        generator = TPCHGenerator(output_dir)
        result_path = generator.generate(scale_factor=scale_factor, format=format)
        
        click.secho(f"✓ Dataset generated: {result_path}", fg='green')
        
        # Validate generated data
        click.echo("Validating dataset...")
        validator = DatasetValidator()
        sf_str = str(scale_factor) if scale_factor >= 1 else 'tiny'
        validation_result = validator.validate_tpch_dataset(result_path, sf_str)
        
        if validation_result['valid']:
            click.secho("✓ Validation passed", fg='green')
        else:
            click.secho("✗ Validation failed:", fg='yellow')
            for error in validation_result['errors']:
                click.echo(f"  - {error}")
        
        # Register dataset
        registry_path = output_dir / "registry.yaml"
        registry = DatasetRegistry(registry_path)
        
        # Compute metadata
        row_counts = {
            table: validation_result['tables'][table]['row_count']
            for table in validation_result['tables']
            if validation_result['tables'][table].get('valid')
        }
        
        checksums = {
            table: validation_result['tables'][table]['checksum']
            for table in validation_result['tables']
            if validation_result['tables'][table].get('valid')
        }
        
        total_size = sum(
            validation_result['tables'][table].get('size_bytes', 0)
            for table in validation_result['tables']
        )
        
        metadata = DatasetMetadata(
            name=dataset,
            benchmark_type='tpch',  # TPC-H benchmark type
            type='generated',
            format=format,
            scale_factor=scale_factor,
            size_bytes=total_size,
            location=str(result_path),
            tables=list(row_counts.keys()),
            row_counts=row_counts,
            checksums=checksums,
            properties={'tpch_version': '3.0'},
            created_at=datetime.now().isoformat(),
            generator='tpch-dbgen'
        )
        
        registry.register(metadata)
        click.secho(f"✓ Dataset registered in {registry_path}", fg='green')
        
        # Display summary
        click.echo("\nDataset Summary:")
        click.echo(f"  Tables: {len(row_counts)}")
        click.echo(f"  Total rows: {sum(row_counts.values()):,}")
        click.echo(f"  Total size: {total_size / (1024**2):.2f} MB")
        
    except Exception as e:
        click.secho(f"✗ Failed to generate dataset: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()


@data_group.command(name="load")
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
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    datasets_root = Path(full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets"))
    
    # Handle Kubernetes port forwarding
    if kind:
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
        
        # Get Trino connection parameters from config
        trino_config = full_config.get("tribench", {}).get("systems", {}).get("trino", {})
        coordinator_config = trino_config.get("coordinator", {})
        
        # Build connection config
        connection_params = ConnectionConfig.from_dict({
            'host': coordinator_config.get('host', Defaults.Trino.HOST),
            'port': coordinator_config.get('port', Defaults.Trino.PORT),
            'user': Defaults.Trino.USER
        })
        
        # Route to appropriate loader based on catalog
        if catalog == 'iceberg':
            # Use fast Iceberg loader with CTAS
            from tribench.data.iceberg_loader import IcebergDataLoader
            
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
            from datetime import datetime
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
            from tribench.data.dataset import BenchmarkType, SchemaFactory
            
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


@data_group.command(name="load-iceberg", deprecated=True, hidden=True)
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


@data_group.command(name="list")
@click.option('--filter', help='Filter datasets by pattern.')
@click.option('--generated-only', is_flag=True, help='Show only generated datasets.')
@config_option
@verbose_option
@click.pass_context
def list_datasets(ctx, filter, generated_only, config, verbose):
    """List available datasets.
    
    \b
    Examples:
        tribench data list
        tribench data list --filter "tpch*"
        tribench data list --generated-only
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    datasets_root = Path(full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets"))
    
    if ctx.obj.verbose:
        click.echo(f"Datasets directory: {datasets_root}")
        if filter:
            click.echo(f"Filter: {filter}")
        if generated_only:
            click.echo("Showing generated datasets only")
    
    try:
        registry_path = datasets_root / "registry.yaml"
        if not registry_path.exists():
            click.echo("No datasets registered yet.")
            click.echo(f"Generate datasets with: tribench data generate <dataset>")
            return
        
        registry = DatasetRegistry(registry_path)
        datasets = registry.list()
        
        if generated_only:
            datasets = [d for d in datasets if d.type == 'generated']
        
        if filter:
            import fnmatch
            datasets = [d for d in datasets if fnmatch.fnmatch(d.name, filter)]
        
        if not datasets:
            click.echo("No datasets found matching criteria.")
            return
        
        click.echo(f"\nFound {len(datasets)} dataset(s):\n")
        
        for ds in datasets:
            click.echo(f"  {ds.name}")
            click.echo(f"    Type: {ds.type}")
            click.echo(f"    Format: {ds.format}")
            if ds.scale_factor:
                click.echo(f"    Scale Factor: {ds.scale_factor}")
            click.echo(f"    Tables: {len(ds.tables)}")
            click.echo(f"    Total Rows: {sum(ds.row_counts.values()):,}")
            if ds.size_bytes:
                click.echo(f"    Size: {ds.size_bytes / (1024**2):.2f} MB")
            click.echo(f"    Location: {ds.location}")
            click.echo(f"    Created: {ds.created_at}")
            click.echo()
            
    except Exception as e:
        click.secho(f"✗ Failed to list datasets: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()


@data_group.command(name="info")
@click.argument("dataset")
@click.option('--detailed', is_flag=True, help='Show detailed statistics.')
@config_option
@verbose_option
@click.pass_context
def info(ctx, dataset, detailed, config, verbose):
    """Show dataset information.
    
    \b
    Examples:
        tribench data info tpch-sf1
        tribench data info tpch-sf1 --detailed
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    datasets_root = Path(full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets"))
    
    if ctx.obj.verbose:
        click.echo(f"Dataset: {dataset}")
        if detailed:
            click.echo("Detailed mode enabled")
    
    try:
        registry_path = datasets_root / "registry.yaml"
        if not registry_path.exists():
            click.secho(f"✗ Dataset registry not found", fg='red')
            return
        
        registry = DatasetRegistry(registry_path)
        metadata = registry.get(dataset)
        
        if not metadata:
            click.secho(f"✗ Dataset '{dataset}' not found in registry", fg='red')
            return
        
        # Display dataset information
        click.echo(f"\nDataset: {metadata.name}")
        click.echo("=" * 60)
        click.echo(f"Type: {metadata.type}")
        click.echo(f"Format: {metadata.format}")
        
        if metadata.scale_factor:
            click.echo(f"Scale Factor: {metadata.scale_factor}")
        
        if metadata.generator:
            click.echo(f"Generator: {metadata.generator}")
        
        click.echo(f"Location: {metadata.location}")
        click.echo(f"Created: {metadata.created_at}")
        
        if metadata.size_bytes:
            size_mb = metadata.size_bytes / (1024**2)
            size_gb = metadata.size_bytes / (1024**3)
            if size_gb >= 1:
                click.echo(f"Total Size: {size_gb:.2f} GB")
            else:
                click.echo(f"Total Size: {size_mb:.2f} MB")
        
        click.echo(f"\nTables ({len(metadata.tables)}):")
        
        for table in metadata.tables:
            row_count = metadata.row_counts.get(table, 0)
            click.echo(f"  - {table}: {row_count:,} rows")
        
        total_rows = sum(metadata.row_counts.values())
        click.echo(f"\nTotal Rows: {total_rows:,}")
        
        # Display Iceberg-specific metadata if format is Iceberg
        if metadata.format == 'iceberg':
            click.echo("\n" + "=" * 60)
            click.echo("Iceberg Metadata:")
            click.echo("=" * 60)
            
            if metadata.iceberg_catalog:
                click.echo(f"Catalog: {metadata.iceberg_catalog}")
            
            if metadata.iceberg_schema:
                click.echo(f"Schema: {metadata.iceberg_schema}")
            
            if metadata.format_version:
                click.echo(f"Format Version: v{metadata.format_version}")
            
            if metadata.storage_location:
                click.echo(f"Storage Location: {metadata.storage_location}")
            
            if metadata.snapshot_ids:
                click.echo(f"\nSnapshot IDs:")
                for table, snapshot_id in metadata.snapshot_ids.items():
                    timestamp = ""
                    if metadata.snapshot_timestamps and table in metadata.snapshot_timestamps:
                        timestamp = f" (at {metadata.snapshot_timestamps[table]})"
                    click.echo(f"  - {table}: {snapshot_id}{timestamp}")
            
            if metadata.manifest_counts:
                click.echo(f"\nManifest Files:")
                total_manifests = sum(metadata.manifest_counts.values())
                for table, count in metadata.manifest_counts.items():
                    click.echo(f"  - {table}: {count} manifests")
                click.echo(f"Total Manifests: {total_manifests}")
        
        if detailed:
            click.echo("\nProperties:")
            for key, value in metadata.properties.items():
                click.echo(f"  {key}: {value}")
            
            if metadata.checksums:
                click.echo("\nChecksums (first 3 tables):")
                for i, (table, checksum) in enumerate(list(metadata.checksums.items())[:3]):
                    click.echo(f"  {table}: {checksum[:16]}...")
        
    except Exception as e:
        click.secho(f"✗ Failed to get dataset info: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()


@data_group.command(name="validate")
@click.argument("dataset")
@click.option('--checksums', is_flag=True, help='Verify checksums.')
@click.option('--row-counts', is_flag=True, help='Verify row counts.')
@config_option
@verbose_option
@click.pass_context
def validate(ctx, dataset, checksums, row_counts, config, verbose):
    """Validate a dataset.
    
    \b
    Examples:
        tribench data validate tpch-sf1
        tribench data validate tpch-sf1 --checksums --row-counts
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    datasets_root = Path(full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets"))
    
    if ctx.obj.verbose:
        click.echo(f"Validating dataset: {dataset}")
        if checksums:
            click.echo("Checking checksums")
        if row_counts:
            click.echo("Checking row counts")
    
    try:
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
        
        click.echo(f"Validating {dataset}...")
        
        # Run validation
        validator = DatasetValidator()
        
        # Determine scale factor string
        if metadata.scale_factor:
            sf_str = str(metadata.scale_factor) if metadata.scale_factor >= 1 else 'tiny'
        else:
            sf_str = 'tiny'
        
        validation_result = validator.validate_tpch_dataset(dataset_path, sf_str)
        
        if validation_result['valid']:
            click.secho("✓ Dataset is valid", fg='green')
        else:
            click.secho("✗ Dataset validation failed", fg='red')
            for error in validation_result['errors']:
                click.echo(f"  - {error}")
            return
        
        # Additional checks
        errors = []
        
        if row_counts:
            click.echo("\nVerifying row counts...")
            for table in validation_result['tables']:
                actual = validation_result['tables'][table].get('row_count')
                expected = metadata.row_counts.get(table)
                
                if actual != expected:
                    errors.append(f"Row count mismatch in {table}: expected {expected}, got {actual}")
                    click.secho(f"  ✗ {table}: {actual} != {expected}", fg='yellow')
                else:
                    click.secho(f"  ✓ {table}: {actual:,} rows", fg='green')
        
        if checksums:
            click.echo("\nVerifying checksums...")
            for table in validation_result['tables']:
                actual = validation_result['tables'][table].get('checksum')
                expected = metadata.checksums.get(table)
                
                if actual != expected:
                    errors.append(f"Checksum mismatch in {table}")
                    click.secho(f"  ✗ {table}: checksum mismatch", fg='yellow')
                else:
                    click.secho(f"  ✓ {table}: checksum valid", fg='green')
        
        if errors:
            click.echo(f"\n{len(errors)} issue(s) found:")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.secho("\n✓ All validation checks passed", fg='green')
            
    except Exception as e:
        click.secho(f"✗ Failed to validate dataset: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()


@data_group.command(name="validate-iceberg")
@click.option('--catalog', default='iceberg', help='Iceberg catalog name.')
@click.option('--schema', default='tpch', help='Schema/database name.')
@click.option('--scale-factor', 
              type=click.Choice(['tiny', '1', '10']),
              default='tiny',
              help='Scale factor for row count validation.')
@click.option('--tables', help='Comma-separated list of tables to validate (default: all TPC-H tables).')
@click.option('--detailed', is_flag=True, help='Show detailed validation results.')
@kind_option
@config_option
@verbose_option
@click.pass_context
def validate_iceberg(ctx, catalog, schema, scale_factor, tables, detailed, kind, config, verbose):
    """Validate Iceberg tables in Trino.
    
    Performs comprehensive validation including:
    - Table existence and accessibility
    - Row count verification against expected values
    - Schema inspection
    - Iceberg metadata validation (snapshots, manifests)
    
    For Kubernetes deployments, use --kind to ensure port forwarding is active.
    
    \b
    Examples:
        tribench data validate-iceberg
        tribench data validate-iceberg --catalog iceberg --schema tpch
        tribench data validate-iceberg --scale-factor 1 --detailed
        tribench data validate-iceberg --tables nation,region,customer
        tribench data validate-iceberg --kind  # For Kubernetes deployments
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    
    # Handle Kubernetes port forwarding
    if kind:
        if not ensure_k8s_port_forwarding(full_config):
            return
    else:
        # Auto-detect and ensure Trino connection
        auto_ensure_trino_connection(full_config)
    
    if ctx.obj.verbose:
        click.echo(f"Validating Iceberg dataset")
        click.echo(f"Catalog: {catalog}")
        click.echo(f"Schema: {schema}")
        click.echo(f"Scale factor: {scale_factor}")
        if tables:
            click.echo(f"Tables: {tables}")
    
    try:
        # Get Trino connection parameters from config
        trino_config = full_config.get("tribench", {}).get("systems", {}).get("trino", {})
        coordinator_config = trino_config.get("coordinator", {})
        
        # Build connection config
        connection_config = ConnectionConfig.from_dict({
            'host': coordinator_config.get('host', Defaults.Trino.HOST),
            'port': coordinator_config.get('port', Defaults.Trino.PORT),
            'user': Defaults.Trino.USER
        })
        
        # Create validator
        validator = IcebergValidator(connection_config)
        
        # Determine tables to validate
        if tables:
            table_list = [t.strip() for t in tables.split(',')]
        else:
            # Default TPC-H tables
            table_list = ['nation', 'region', 'customer', 'supplier', 
                         'part', 'partsupp', 'orders', 'lineitem']
        
        click.echo(f"\nValidating {len(table_list)} Iceberg tables in {catalog}.{schema}...")
        
        # Run validation
        results = validator.validate_iceberg_dataset(
            catalog=catalog,
            schema=schema,
            tables=table_list,
            scale_factor=scale_factor,
            benchmark_type='tpch'
        )
        
        # Display results
        if results['valid']:
            click.secho("\n✓ All tables are valid", fg='green')
        else:
            click.secho("\n✗ Validation failed", fg='red')
        
        # Summary
        summary = results.get('summary', {})
        click.echo(f"\nSummary:")
        click.echo(f"  Valid tables: {summary.get('valid_tables', 0)}/{summary.get('total_tables', 0)}")
        click.echo(f"  Total rows: {summary.get('total_rows', 0):,}")
        click.echo(f"  Total snapshots: {summary.get('total_snapshots', 0)}")
        
        # Table details
        if detailed or not results['valid']:
            click.echo(f"\nTable validation details:")
            for table_name, table_result in results['tables'].items():
                status = "✓" if table_result['valid'] else "✗"
                color = 'green' if table_result['valid'] else 'red'
                
                click.secho(f"\n  {status} {table_name}:", fg=color)
                click.echo(f"    Rows: {table_result.get('row_count', 0):,}")
                
                if 'expected_row_count' in table_result:
                    expected = table_result['expected_row_count']
                    actual = table_result.get('row_count', 0)
                    match = "✓" if actual == expected else "✗"
                    click.echo(f"    Expected: {expected:,} {match}")
                
                click.echo(f"    Columns: {table_result.get('column_count', 0)}")
                click.echo(f"    Snapshots: {table_result.get('snapshot_count', 0)}")
                click.echo(f"    Data files: {table_result.get('file_count', 0)}")
                
                if table_result.get('errors'):
                    click.secho(f"    Errors:", fg='red')
                    for error in table_result['errors']:
                        click.echo(f"      - {error}")
                
                if table_result.get('warnings'):
                    click.secho(f"    Warnings:", fg='yellow')
                    for warning in table_result['warnings']:
                        click.echo(f"      - {warning}")
        
        # Overall errors
        if results.get('errors'):
            click.echo(f"\nValidation errors:")
            for error in results['errors']:
                click.secho(f"  - {error}", fg='red')
        
        # Warnings
        if results.get('warnings'):
            click.echo(f"\nWarnings:")
            for warning in results['warnings']:
                click.secho(f"  - {warning}", fg='yellow')
        
        # Exit with error code if validation failed
        if not results['valid']:
            ctx.exit(1)
            
    except Exception as e:
        click.secho(f"\n✗ Failed to validate Iceberg dataset: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)
