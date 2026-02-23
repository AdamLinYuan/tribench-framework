"""Dataset generation commands."""

import click
from pathlib import Path
from datetime import datetime
import logging

from tribench.cli.base import dry_run_option, verbose_option, config_option
from tribench.data.dataset import (
    TPCHGenerator,
    TPCDSGenerator,
    DatasetRegistry,
    DatasetValidator,
    DatasetMetadata
)
from .utils import get_datasets_root

logger = logging.getLogger(__name__)


@click.command(name="generate")
@click.argument("dataset", type=click.Choice([
    'tpch-tiny', 'tpch-sf1', 'tpch-sf10', 'tpch-sf100',
    'tpcds-tiny', 'tpcds-sf1', 'tpcds-sf10', 'tpcds-sf100'
]))
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
        tribench data generate tpcds-tiny --format parquet
        tribench data generate tpch-sf10 --output /data/tpch --dry-run
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Determine benchmark type
    benchmark_type = 'tpch' if dataset.startswith('tpch') else 'tpcds'
    
    # Parse scale factor from dataset name
    scale_factor_map = {
        'tpch-tiny': 0.01,
        'tpch-sf1': 1.0,
        'tpch-sf10': 10.0,
        'tpch-sf100': 100.0,
        'tpcds-tiny': 0.01,
        'tpcds-sf1': 1.0,
        'tpcds-sf10': 10.0,
        'tpcds-sf100': 100.0
    }
    scale_factor = scale_factor_map[dataset]
    
    # Determine output directory
    if output:
        output_dir = Path(output)
    else:
        bundle_root = getattr(ctx.obj, 'bundle_root', None)
        datasets_root = get_datasets_root(config, bundle_root=bundle_root)
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
        sf_str = str(scale_factor).replace('.', '_')
        dataset_path = output_dir / f"{benchmark_type}-sf{sf_str}" / format
        if dataset_path.exists() and not overwrite:
            click.secho(f"✗ Dataset already exists at {dataset_path}", fg='red')
            click.echo("Use --overwrite to regenerate")
            return
        
        click.echo(f"Generating {dataset}...")
        
        # Generate dataset based on benchmark type
        if benchmark_type == 'tpch':
            generator = TPCHGenerator(output_dir)
            result_path = generator.generate(scale_factor=scale_factor, format=format)
        else:  # tpcds
            generator = TPCDSGenerator(output_dir)
            result_path = generator.generate(scale_factor=scale_factor, format=format)
        
        click.secho(f"✓ Dataset generated: {result_path}", fg='green')
        
        # Validate generated data
        click.echo("Validating dataset...")
        validator = DatasetValidator()
        sf_str = str(scale_factor) if scale_factor >= 1 else 'tiny'
        
        if benchmark_type == 'tpch':
            validation_result = validator.validate_tpch_dataset(result_path, sf_str)
        else:  # tpcds - generic validation
            validation_result = {
                'valid': True,
                'tables': {},
                'errors': []
            }
            # Get expected tables for TPC-DS
            from tribench.data.dataset import TPCDSSchema
            schema = TPCDSSchema()
            for table_name in schema.get_tables():
                parquet_file = result_path / f"{table_name}.parquet"
                if parquet_file.exists():
                    table_validation = validator.validate_parquet_file(parquet_file)
                    validation_result['tables'][table_name] = table_validation
                    if not table_validation.get('valid'):
                        validation_result['valid'] = False
                        validation_result['errors'].append(
                            f"Invalid table {table_name}: {table_validation.get('error')}"
                        )
                else:
                    validation_result['errors'].append(f"Missing table: {table_name}")
                    validation_result['valid'] = False
        
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
        
        # Determine properties and generator based on benchmark type
        if benchmark_type == 'tpch':
            properties = {'tpch_version': '3.0'}
            generator_name = 'tpch-dbgen'
        else:  # tpcds
            properties = {'tpcds_version': '2.0'}
            generator_name = 'tpcds-dsdgen'
        
        metadata = DatasetMetadata(
            name=dataset,
            benchmark_type=benchmark_type,
            type='generated',
            format=format,
            scale_factor=scale_factor,
            size_bytes=total_size,
            location=str(result_path),
            tables=list(row_counts.keys()),
            row_counts=row_counts,
            checksums=checksums,
            properties=properties,
            created_at=datetime.now().isoformat(),
            generator=generator_name
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
