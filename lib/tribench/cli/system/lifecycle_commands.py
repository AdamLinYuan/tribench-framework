"""
System lifecycle commands.

Commands for setting up, starting, stopping, and tearing down systems.
"""

import click
from tribench.cli.base import dry_run_option, verbose_option, config_option, should_use_kubernetes
from tribench.systems.trino import TrinoSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.utils.config import ConfigurationLoader
from .utils import get_k8s_system


def _load_cfg(ctx, config_path=None):
    """Load config with bundle_root taken from Click context if available."""
    bundle_root = getattr(ctx.obj, 'bundle_root', None)
    loader = ConfigurationLoader(bundle_root=bundle_root)
    return loader.load(experiment_config=config_path) if config_path else loader.load()


@click.command(name="setup")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@click.option('--version', help='System version to install.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def setup(ctx, system, version, config, dry_run, verbose):
    """Set up a system (trino, postgresql, minio, hive-metastore, all).
    
    Backend selection (Docker/Kubernetes) is configured in host config files.
    Use 'tribench config profile <name>' to set your preferred backend.
    
    \b
    Examples:
        tribench sys setup trino                    # Uses backend from active profile
        tribench sys setup trino --version 434
        tribench sys setup all --dry-run
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration first to check backend default
    cfg = _load_cfg(ctx, config)
    
    # Determine backend
    use_k8s = should_use_kubernetes(cfg)
    
    if ctx.obj.verbose:
        click.echo(f"Setting up system: {system}")
        if version:
            click.echo(f"Version: {version}")
        backend_name = "Kubernetes" if use_k8s else "Docker Compose"
        click.echo(f"Backend: {backend_name} (from config)")
        if config:
            click.echo(f"Config: {config}")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would setup {system}")
        return
    
    if use_k8s:
        k8s = get_k8s_system(config_tree=cfg)
        
        # Show incremental progress for 'all'
        systems_to_setup = ['postgresql', 'hive-metastore', 'minio', 'trino'] if system == 'all' else [system]
        
        for sys_name in systems_to_setup:
            try:
                component_name = {
                    'postgresql': 'PostgreSQL',
                    'hive-metastore': 'Hive Metastore',
                    'minio': 'MinIO',
                    'trino': 'Trino'
                }.get(sys_name, sys_name)
                
                click.echo(f"Setting up {component_name} on Kubernetes...")
                k8s.setup(component=sys_name)
                click.secho(f"✓ {component_name} setup complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to setup {component_name}: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
                if system != 'all':
                    return
        return

    # Implement system setup
    systems_to_setup = ['trino', 'postgresql', 'minio', 'hive-metastore'] if system == 'all' else [system]
    
    for sys_name in systems_to_setup:
        if sys_name == 'trino':
            try:
                click.echo(f"Setting up Trino...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                # Override version if specified
                if version:
                    from pyhocon import ConfigFactory
                    cfg = ConfigFactory.parse_string(f'tribench.systems.trino.version = "{version}"').with_fallback(cfg)
                
                trino = TrinoSystem(config=cfg)
                trino.setup()
                click.secho(f"✓ Trino setup complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to setup Trino: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'postgresql':
            try:
                click.echo(f"Setting up PostgreSQL...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                # Override version if specified
                if version:
                    from pyhocon import ConfigFactory
                    cfg = ConfigFactory.parse_string(f'tribench.systems.postgresql.version = "{version}"').with_fallback(cfg)
                
                postgresql = PostgreSQLSystem(config=cfg)
                postgresql.setup()
                click.secho(f"✓ PostgreSQL setup complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to setup PostgreSQL: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'minio':
            try:
                click.echo(f"Setting up MinIO...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                minio = MinIOSystem(config=cfg)
                minio.setup()
                click.secho(f"✓ MinIO setup complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to setup MinIO: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'hive-metastore':
            try:
                click.echo(f"Setting up Hive Metastore...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                # Override version if specified
                if version:
                    from pyhocon import ConfigFactory
                    cfg = ConfigFactory.parse_string(f'tribench.systems.hive_metastore.version = "{version}"').with_fallback(cfg)
                
                hive_metastore = HiveMetastoreSystem(config=cfg)
                hive_metastore.setup()
                click.secho(f"✓ Hive Metastore setup complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to setup Hive Metastore: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()


@click.command(name="start")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def start(ctx, system, config, dry_run, verbose):
    """Start a system.
    
    Backend selection (Docker/Kubernetes) is configured in host config files.
    Use 'tribench config profile <name>' to set your preferred backend.
    
    For Kubernetes: When starting all systems, port forwarding is automatically
    configured for Trino and MinIO to enable local access.
    
    \b
    Examples:
        tribench sys start trino          # Uses backend from active profile
        tribench sys start all            # K8s: Starts all + port forwarding
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration first to check backend default
    cfg = _load_cfg(ctx, config)
    
    # Determine backend
    use_k8s = should_use_kubernetes(cfg)
    
    if ctx.obj.verbose:
        click.echo(f"Starting system: {system}")
        backend_name = "Kubernetes" if use_k8s else "Docker Compose"
        click.echo(f"Backend: {backend_name} (from config)")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would start {system}")
        return
    
    if use_k8s:
        k8s = get_k8s_system(config_tree=cfg)
        
        # Show incremental progress for 'all'
        systems_to_start = ['postgresql', 'hive-metastore', 'minio', 'trino'] if system == 'all' else [system]
        
        for sys_name in systems_to_start:
            try:
                component_name = {
                    'postgresql': 'PostgreSQL',
                    'hive-metastore': 'Hive Metastore',
                    'minio': 'MinIO',
                    'trino': 'Trino'
                }.get(sys_name, sys_name)
                
                click.echo(f"Starting {component_name} on Kubernetes...")
                k8s.start(component=sys_name)
                click.secho(f"✓ {component_name} started successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to start {component_name}: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
                if system != 'all':
                    return
        
        # Automatically start port forwarding when starting all systems
        if system == 'all':
            click.echo("")
            click.echo("Starting port forwarding...")
            try:
                # Start both Trino and MinIO port forwards
                k8s.start_port_forwarding(include_minio=True)
                
                # Check status
                trino_active = k8s.is_port_forwarding_active()
                minio_active = k8s.is_minio_port_forwarding_active()
                
                if trino_active and minio_active:
                    from tribench.defaults import Defaults
                    click.secho("✓ Port forwarding active", fg='green')
                    click.echo(f"  Trino:  http://{Defaults.Hosts.LOCALHOST}:{Defaults.Trino.PORT}")
                    click.echo(f"  MinIO:  http://{Defaults.Hosts.LOCALHOST}:{Defaults.MinIO.PORT} (API)")
                    click.echo(f"          http://{Defaults.Hosts.LOCALHOST}:{Defaults.MinIO.CONSOLE_PORT} (Console)")
                elif trino_active:
                    click.secho("⚠ Trino port forwarding active, but MinIO failed", fg='yellow')
                else:
                    click.secho("⚠ Port forwarding failed - start manually with: tribench sys port-forward start", fg='yellow')
            except Exception as e:
                click.secho(f"⚠ Port forwarding failed: {e}", fg='yellow')
                click.echo("  Start manually with: tribench sys port-forward start")
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        
        return

    # Implement system start
    systems_to_start = ['trino', 'postgresql', 'minio', 'hive-metastore'] if system == 'all' else [system]
    
    for sys_name in systems_to_start:
        if sys_name == 'trino':
            try:
                click.echo(f"Starting Trino...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                trino = TrinoSystem(config=cfg)
                trino.start()
                click.secho(f"✓ Trino started successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to start Trino: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'postgresql':
            try:
                click.echo(f"Starting PostgreSQL...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                postgresql = PostgreSQLSystem(config=cfg)
                postgresql.start()
                click.secho(f"✓ PostgreSQL started successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to start PostgreSQL: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'minio':
            try:
                click.echo(f"Starting MinIO...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                minio = MinIOSystem(config=cfg)
                minio.start()
                click.secho(f"✓ MinIO started successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to start MinIO: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'hive-metastore':
            try:
                click.echo(f"Starting Hive Metastore...")
                
                # Load configuration
                cfg = _load_cfg(ctx, config)
                
                hive_metastore = HiveMetastoreSystem(config=cfg)
                hive_metastore.start()
                click.secho(f"✓ Hive Metastore started successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to start Hive Metastore: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()


@click.command(name="stop")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@click.option('--force', is_flag=True, help='Force stop without graceful shutdown.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def stop(ctx, system, force, config, dry_run, verbose):
    """Stop a system.
    
    Backend selection (Docker/Kubernetes) is configured in host config files.
    Use 'tribench config profile <name>' to set your preferred backend.
    
    \b
    Examples:
        tribench sys stop trino           # Uses backend from active profile
        tribench sys stop all --force
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration first to check backend default
    cfg = _load_cfg(ctx, config)
    
    # Determine backend
    use_k8s = should_use_kubernetes(cfg)
    
    if ctx.obj.verbose:
        click.echo(f"Stopping system: {system}")
        if force:
            click.echo("Force stop enabled")
        backend_name = "Kubernetes" if use_k8s else "Docker Compose"
        backend_source = "flag" if kind else "config default"
        click.echo(f"Backend: {backend_name} (from {backend_source})")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would stop {system}")
        return
    
    if use_k8s:
        k8s = get_k8s_system(config_tree=cfg)
        
        # Show incremental progress for 'all'
        systems_to_stop = ['trino', 'minio', 'hive-metastore', 'postgresql'] if system == 'all' else [system]
        
        for sys_name in systems_to_stop:
            try:
                component_name = {
                    'postgresql': 'PostgreSQL',
                    'hive-metastore': 'Hive Metastore',
                    'minio': 'MinIO',
                    'trino': 'Trino'
                }.get(sys_name, sys_name)
                
                click.echo(f"Stopping {component_name} on Kubernetes...")
                k8s.stop(component=sys_name)
                click.secho(f"✓ {component_name} stopped successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to stop {component_name}: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
                if system != 'all':
                    return
        return

    # Implement system stop
    systems_to_stop = ['trino', 'postgresql', 'minio', 'hive-metastore'] if system == 'all' else [system]
    
    for sys_name in systems_to_stop:
        if sys_name == 'trino':
            try:
                click.echo(f"Stopping Trino...")
                trino = TrinoSystem()
                trino.stop(force=force)
                click.secho(f"✓ Trino stopped successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to stop Trino: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'postgresql':
            try:
                click.echo(f"Stopping PostgreSQL...")
                postgresql = PostgreSQLSystem()
                postgresql.stop(force=force)
                click.secho(f"✓ PostgreSQL stopped successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to stop PostgreSQL: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'minio':
            try:
                click.echo(f"Stopping MinIO...")
                minio = MinIOSystem()
                minio.stop(force=force)
                click.secho(f"✓ MinIO stopped successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to stop MinIO: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'hive-metastore':
            try:
                click.echo(f"Stopping Hive Metastore...")
                hive_metastore = HiveMetastoreSystem()
                hive_metastore.stop(force=force)
                click.secho(f"✓ Hive Metastore stopped successfully", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to stop Hive Metastore: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()


@click.command(name="teardown")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@click.option('--keep-data', is_flag=True, help='Keep data after teardown.')
@config_option
@click.confirmation_option(prompt='Are you sure you want to tear down the system?')
@dry_run_option
@verbose_option
@click.pass_context
def teardown(ctx, system, keep_data, config, dry_run, verbose):
    """Tear down a system (destructive operation).
    
    Backend selection (Docker/Kubernetes) is configured in host config files.
    Use 'tribench config profile <name>' to set your preferred backend.
    
    \b
    Examples:
        tribench sys teardown trino       # Uses backend from active profile
        tribench sys teardown all --keep-data
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration first to check backend default
    cfg = _load_cfg(ctx, config)
    
    # Determine backend
    use_k8s = should_use_kubernetes(cfg)
    
    if ctx.obj.verbose:
        click.echo(f"Tearing down system: {system}")
        if keep_data:
            click.echo("Will keep data after teardown")
        backend_name = "Kubernetes" if use_k8s else "Docker Compose"
        backend_source = "flag" if kind else "config default"
        click.echo(f"Backend: {backend_name} (from {backend_source})")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would teardown {system}")
        return
    
    if use_k8s:
        k8s = get_k8s_system(config_tree=cfg)
        
        # Show incremental progress for 'all'
        systems_to_teardown = ['trino', 'minio', 'hive-metastore', 'postgresql'] if system == 'all' else [system]
        
        for sys_name in systems_to_teardown:
            try:
                component_name = {
                    'postgresql': 'PostgreSQL',
                    'hive-metastore': 'Hive Metastore',
                    'minio': 'MinIO',
                    'trino': 'Trino'
                }.get(sys_name, sys_name)
                
                click.echo(f"Tearing down {component_name} on Kubernetes...")
                k8s.teardown(component=sys_name)
                click.secho(f"✓ {component_name} teardown complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to teardown {component_name}: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
                if system != 'all':
                    return
        return

    # Implement system teardown
    systems_to_teardown = ['trino', 'postgresql', 'minio', 'hive-metastore'] if system == 'all' else [system]
    
    for sys_name in systems_to_teardown:
        if sys_name == 'trino':
            try:
                click.echo(f"Tearing down Trino...")
                trino = TrinoSystem()
                trino.teardown(keep_data=keep_data)
                click.secho(f"✓ Trino teardown complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to teardown Trino: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'postgresql':
            try:
                click.echo(f"Tearing down PostgreSQL...")
                postgresql = PostgreSQLSystem()
                postgresql.teardown(keep_data=keep_data)
                click.secho(f"✓ PostgreSQL teardown complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to teardown PostgreSQL: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'minio':
            try:
                click.echo(f"Tearing down MinIO...")
                minio = MinIOSystem()
                minio.teardown(keep_data=keep_data)
                click.secho(f"✓ MinIO teardown complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to teardown MinIO: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'hive-metastore':
            try:
                click.echo(f"Tearing down Hive Metastore...")
                hive_metastore = HiveMetastoreSystem()
                hive_metastore.teardown(keep_data=keep_data)
                click.secho(f"✓ Hive Metastore teardown complete", fg='green')
            except Exception as e:
                click.secho(f"✗ Failed to teardown Hive Metastore: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
