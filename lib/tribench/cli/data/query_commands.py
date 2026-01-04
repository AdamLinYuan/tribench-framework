"""Dataset information and query commands."""

import click
from pathlib import Path
import logging

from tribench.cli.base import verbose_option, config_option
from tribench.data.dataset import DatasetRegistry
from .utils import get_datasets_root

logger = logging.getLogger(__name__)


@click.command(name="list")
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
    
    datasets_root = get_datasets_root(config)
    
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


@click.command(name="info")
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
    
    datasets_root = get_datasets_root(config)
    
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
