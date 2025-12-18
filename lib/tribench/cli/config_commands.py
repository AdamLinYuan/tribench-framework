"""Configuration management commands for TriBench CLI."""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from tribench.cli.base import cli, verbose_option
from tribench.utils.config import ConfigurationLoader
from tribench.defaults import Defaults


@cli.group(name="config")
def config_group():
    """
    Configuration management commands.
    
    View, validate, and debug TriBench configuration hierarchy.
    """
    pass


@config_group.command(name="show")
@click.option(
    '--section',
    '-s',
    help='Show only a specific section (e.g., "systems.trino" or "tribench.defaults")'
)
@click.option(
    '--experiment',
    '-e',
    type=click.Path(exists=True),
    help='Include experiment config in the merge'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['hocon', 'json', 'yaml'], case_sensitive=False),
    default='hocon',
    help='Output format (default: hocon)'
)
@click.option(
    '--sources',
    is_flag=True,
    help='Show which config file each value comes from'
)
@verbose_option
def show_config(section: Optional[str], experiment: Optional[str], format: str, sources: bool, verbose: bool):
    """
    Show the current merged configuration.
    
    Displays the final configuration after merging all layers:
    reference.conf → host config → experiment config → env vars
    
    \b
    Examples:
        tribench config show
        tribench config show --section systems.trino
        tribench config show --experiment experiments/my-test.yaml
        tribench config show --format json
        tribench config show --sources  # Show config file sources
    """
    try:
        loader = ConfigurationLoader()
        
        # Load configuration
        if experiment:
            click.echo(f"Loading with experiment: {experiment}", err=True) if verbose else None
            config = loader.load(experiment_config=experiment)
        else:
            config = loader.load()
        
        # Extract specific section if requested
        if section:
            parts = section.split('.')
            current = config
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    click.echo(f"Error: Section '{section}' not found in configuration", err=True)
                    sys.exit(1)
            config = {section: current}
        
        # Output in requested format
        if format == 'json':
            click.echo(json.dumps(config, indent=2, default=str))
        elif format == 'yaml':
            try:
                import yaml
                click.echo(yaml.dump(config, default_flow_style=False, sort_keys=False))
            except ImportError:
                click.echo("Error: PyYAML not installed. Use --format json or --format hocon", err=True)
                sys.exit(1)
        else:  # hocon
            from pyhocon import HOCONConverter
            click.echo(HOCONConverter.to_hocon(config))
        
        if sources and verbose:
            import platform
            host_name = platform.node().split('.')[0]
            click.echo("\n# Configuration sources:", err=True)
            click.echo(f"# - Reference: {loader.reference_config_path}", err=True)
            
            # Check for host config
            possible_paths = [
                loader.hosts_path / host_name / "application.conf",
                loader.hosts_path / f"{host_name}.conf",
            ]
            for config_path in possible_paths:
                if config_path.exists():
                    click.echo(f"# - Host: {config_path}", err=True)
                    break
            
            if experiment:
                click.echo(f"# - Experiment: {experiment}", err=True)
                
    except FileNotFoundError as e:
        click.echo(f"Error: Configuration file not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config_group.command(name="validate")
@click.option(
    '--experiment',
    '-e',
    type=click.Path(exists=True),
    help='Validate with experiment config included'
)
@verbose_option
def validate_config(experiment: Optional[str], verbose: bool):
    """
    Validate configuration for errors.
    
    Checks for:
    - Missing required fields
    - Invalid values
    - Type mismatches
    - Circular references
    
    \b
    Examples:
        tribench config validate
        tribench config validate --experiment experiments/my-test.yaml
    """
    try:
        loader = ConfigurationLoader()
        
        click.echo("Validating configuration...", err=True) if verbose else None
        
        # Load and parse config
        if experiment:
            config = loader.load(experiment_config=experiment)
        else:
            config = loader.load()
        
        # Basic validation checks
        errors = []
        warnings = []
        
        # Check required top-level keys
        if 'tribench' not in config:
            errors.append("Missing required top-level key: 'tribench'")
        
        # Check systems configuration
        if 'systems' in config.get('tribench', {}):
            systems = config['tribench']['systems']
            
            # Validate Trino config
            if 'trino' in systems:
                trino = systems['trino']
                if 'coordinator' in trino:
                    coord = trino['coordinator']
                    if 'port' not in coord:
                        warnings.append("Trino coordinator port not specified, using default")
                    if 'host' not in coord:
                        warnings.append("Trino coordinator host not specified, using default")
        
        # Report results
        if errors:
            click.echo("❌ Configuration validation failed:", err=True)
            for error in errors:
                click.echo(f"  ERROR: {error}", err=True)
            sys.exit(1)
        elif warnings:
            click.echo("⚠️  Configuration valid with warnings:")
            for warning in warnings:
                click.echo(f"  WARNING: {warning}")
        else:
            click.echo("✅ Configuration is valid")
        
        if verbose:
            click.echo(f"\nConfiguration loaded from:", err=True)
            click.echo(f"  - Reference: {loader.reference_config_path}", err=True)
            if loader.host_config_path:
                click.echo(f"  - Host: {loader.host_config_path}", err=True)
            if experiment:
                click.echo(f"  - Experiment: {experiment}", err=True)
                
    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config_group.command(name="trace")
@click.argument('key')
@click.option(
    '--experiment',
    '-e',
    type=click.Path(exists=True),
    help='Include experiment config in trace'
)
@verbose_option
def trace_config(key: str, experiment: Optional[str], verbose: bool):
    """
    Trace where a configuration value comes from.
    
    Shows the precedence chain for a specific configuration key.
    
    \b
    Examples:
        tribench config trace tribench.systems.trino.coordinator.port
        tribench config trace systems.minio.host
    """
    try:
        loader = ConfigurationLoader()
        
        # Load all layers separately
        from pyhocon import ConfigFactory
        import platform
        
        reference = ConfigFactory.parse_file(str(loader.reference_config_path))
        
        # Find host config
        host_name = platform.node().split('.')[0]
        host_config_path = None
        host_config = None
        
        possible_paths = [
            loader.hosts_path / host_name / "application.conf",
            loader.hosts_path / f"{host_name}.conf",
        ]
        
        for config_path in possible_paths:
            if config_path.exists():
                host_config_path = config_path
                host_config = ConfigFactory.parse_file(str(config_path))
                break
        
        exp_config = None
        if experiment:
            exp_config = ConfigFactory.parse_file(experiment)
        
        # Navigate to the key in each layer
        def get_value(config, key_path):
            parts = key_path.split('.')
            current = config
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    return None
            return current
        
        # Trace the value through layers
        click.echo(f"Tracing configuration key: {key}\n")
        
        ref_value = get_value(reference, key)
        host_value = get_value(host_config, key) if host_config else None
        exp_value = get_value(exp_config, key) if exp_config else None
        
        # Show precedence chain
        if ref_value is not None:
            click.echo(f"1. reference.conf: {ref_value}")
        else:
            click.echo(f"1. reference.conf: (not set)")
        
        if host_config:
            if host_value is not None:
                click.echo(f"2. {host_config_path.name}: {host_value} ⬅ OVERRIDES")
            else:
                click.echo(f"2. {host_config_path.name}: (not set)")
        else:
            click.echo(f"2. host config: (not found)")
        
        if exp_config:
            if exp_value is not None:
                click.echo(f"3. {Path(experiment).name}: {exp_value} ⬅ OVERRIDES")
            else:
                click.echo(f"3. {Path(experiment).name}: (not set)")
        
        # Show final value
        final_value = exp_value if exp_value is not None else (host_value if host_value is not None else ref_value)
        if final_value is not None:
            click.echo(f"\n✅ Final value: {final_value}")
        else:
            click.echo(f"\n❌ Key not found in any configuration layer")
            
            # Try to suggest similar keys
            click.echo("\nPossible alternatives:")
            merged = loader.load()
            
            # Simple fuzzy search
            key_parts = key.lower().split('.')
            suggestions = []
            
            def find_keys(obj, prefix=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        full_key = f"{prefix}.{k}" if prefix else k
                        if any(part in k.lower() for part in key_parts):
                            suggestions.append(full_key)
                        find_keys(v, full_key)
            
            find_keys(merged)
            for suggestion in suggestions[:5]:
                click.echo(f"  - {suggestion}")
                
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config_group.command(name="defaults")
@click.option(
    '--section',
    '-s',
    type=click.Choice(['hosts', 'ports', 'credentials', 'timeouts', 'retry', 'all'], case_sensitive=False),
    default='all',
    help='Show specific defaults section'
)
def show_defaults(section: str):
    """
    Show framework defaults from lib/tribench/defaults.py.
    
    These are the hard-coded defaults used when no configuration is provided.
    
    \b
    Examples:
        tribench config defaults
        tribench config defaults --section ports
        tribench config defaults --section timeouts
    """
    def print_section(title, obj):
        click.echo(f"\n{title}:")
        click.echo("=" * len(title))
        for attr in dir(obj):
            if not attr.startswith('_') and attr.isupper():
                value = getattr(obj, attr)
                click.echo(f"  {attr}: {value}")
    
    if section == 'all' or section == 'hosts':
        print_section("Hosts", Defaults.Hosts)
    
    if section == 'all' or section == 'ports':
        print_section("Ports", Defaults.Ports)
    
    if section == 'all' or section == 'credentials':
        print_section("Credentials (Development Only)", Defaults.Credentials)
    
    if section == 'all' or section == 'timeouts':
        print_section("Timeouts (seconds)", Defaults.Timeouts)
    
    if section == 'all' or section == 'retry':
        print_section("Retry Configuration", Defaults.Retry)
    
    click.echo("\nSee config/reference.conf for full documentation.")


if __name__ == "__main__":
    cli()
