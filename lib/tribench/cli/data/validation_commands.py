"""Dataset validation commands."""

import click
from pathlib import Path
import logging

from tribench.cli.base import verbose_option, config_option, kind_option, ensure_k8s_port_forwarding, auto_ensure_trino_connection
from tribench.data.dataset import DatasetRegistry, DatasetValidator
from tribench.data.iceberg_validator import IcebergValidator
from .utils import get_datasets_root, get_trino_connection_params

logger = logging.getLogger(__name__)


@click.command(name="validate")
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
    
    datasets_root = get_datasets_root(config)
    
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


@click.command(name="validate-iceberg")
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
    from tribench.utils.config import ConfigurationLoader
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
        # Get Trino connection parameters
        connection_config = get_trino_connection_params(config)
        
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
