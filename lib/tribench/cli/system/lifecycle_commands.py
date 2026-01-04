"""
System lifecycle commands.

Commands for setting up, starting, stopping, and tearing down systems.
"""

import click
from tribench.cli.base import dry_run_option, verbose_option, config_option
from tribench.systems.trino import TrinoSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.utils.config import ConfigurationLoader
from .utils import get_k8s_system


@click.command(name="setup")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@click.option('--version', help='System version to install.')
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def setup(ctx, system, version, kind, config, dry_run, verbose):
    """Set up a system (trino, postgresql, minio, hive-metastore, all).
    
    \b
    Examples:
        tribench sys setup trino
        tribench sys setup trino --version 434
        tribench sys setup all --dry-run
        tribench sys setup all --kind
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Setting up system: {system}")
        if version:
            click.echo(f"Version: {version}")
        if kind:
            click.echo("Backend: Kubernetes")
        if config:
            click.echo(f"Config: {config}")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would setup {system}")
        return
    
    if kind:
        try:
            click.echo(f"Setting up {system} on Kubernetes...")
            
            # Load configuration to pass to K8s system
            loader = ConfigurationLoader()
            cfg = loader.load(experiment_config=config) if config else loader.load()
            
            k8s = get_k8s_system(config_tree=cfg)
            k8s.setup(component=system)
            click.secho(f"✓ Kubernetes {system} setup complete", fg='green')
        except Exception as e:
            click.secho(f"✗ Failed to setup Kubernetes {system}: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
        return

    # Implement system setup
    systems_to_setup = ['trino', 'postgresql', 'minio', 'hive-metastore'] if system == 'all' else [system]
    
    for sys_name in systems_to_setup:
        if sys_name == 'trino':
            try:
                click.echo(f"Setting up Trino...")
                
                # Load configuration
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def start(ctx, system, kind, config, dry_run, verbose):
    """Start a system.
    
    \b
    Examples:
        tribench sys start trino
        tribench sys start all
        tribench sys start all --kind
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Starting system: {system}")
        if kind:
            click.echo("Backend: Kubernetes")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would start {system}")
        return
    
    if kind:
        try:
            click.echo(f"Starting {system} on Kubernetes...")
            
            # Load configuration to pass to K8s system
            loader = ConfigurationLoader()
            cfg = loader.load(experiment_config=config) if config else loader.load()
            
            k8s = get_k8s_system(config_tree=cfg)
            k8s.start(component=system)
            click.secho(f"✓ Kubernetes {system} started successfully", fg='green')
        except Exception as e:
            click.secho(f"✗ Failed to start Kubernetes {system}: {e}", fg='red')
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
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
                loader = ConfigurationLoader()
                cfg = loader.load(experiment_config=config) if config else loader.load()
                
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
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
@dry_run_option
@verbose_option
@click.pass_context
def stop(ctx, system, force, kind, dry_run, verbose):
    """Stop a system.
    
    \b
    Examples:
        tribench sys stop trino
        tribench sys stop all --force
        tribench sys stop all --kind
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Stopping system: {system}")
        if force:
            click.echo("Force stop enabled")
        if kind:
            click.echo("Backend: Kubernetes")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would stop {system}")
        return
    
    if kind:
        try:
            click.echo(f"Stopping {system} on Kubernetes...")
            k8s = get_k8s_system()
            k8s.stop(component=system)
            click.secho(f"✓ Kubernetes {system} stopped successfully", fg='green')
        except Exception as e:
            click.secho(f"✗ Failed to stop Kubernetes {system}: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
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
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
@click.confirmation_option(prompt='Are you sure you want to tear down the system?')
@dry_run_option
@verbose_option
@click.pass_context
def teardown(ctx, system, keep_data, kind, dry_run, verbose):
    """Tear down a system (destructive operation).
    
    \b
    Examples:
        tribench sys teardown trino
        tribench sys teardown all --keep-data
        tribench sys teardown all --kind
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Tearing down system: {system}")
        if keep_data:
            click.echo("Will keep data after teardown")
        if kind:
            click.echo("Backend: Kubernetes")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would teardown {system}")
        return
    
    if kind:
        try:
            click.echo(f"Tearing down {system} on Kubernetes...")
            k8s = get_k8s_system()
            k8s.teardown(component=system)
            click.secho(f"✓ Kubernetes {system} teardown complete", fg='green')
        except Exception as e:
            click.secho(f"✗ Failed to teardown Kubernetes {system}: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
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
