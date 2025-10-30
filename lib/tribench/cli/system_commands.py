"""System management commands."""

import click
from pathlib import Path
from tribench.cli.base import cli, dry_run_option, verbose_option, config_option
from tribench.systems.trino import TrinoSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.utils.config import ConfigurationLoader


@cli.group(name="sys")
def system_group():
    """System lifecycle management commands.
    
    Manage Trino, PostgreSQL, MinIO and other system components.
    """
    pass


@system_group.command(name="setup")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@click.option('--version', help='System version to install.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def setup(ctx, system, version, config, dry_run, verbose):
    """Set up a system (trino, postgresql, minio, hive-metastore, all).
    
    \b
    Examples:
        tribench sys setup trino
        tribench sys setup trino --version 434
        tribench sys setup all --dry-run
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Setting up system: {system}")
        if version:
            click.echo(f"Version: {version}")
        if config:
            click.echo(f"Config: {config}")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would setup {system}")
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


@system_group.command(name="start")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def start(ctx, system, config, dry_run, verbose):
    """Start a system.
    
    \b
    Examples:
        tribench sys start trino
        tribench sys start all
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Starting system: {system}")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would start {system}")
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


@system_group.command(name="stop")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@click.option('--force', is_flag=True, help='Force stop without graceful shutdown.')
@dry_run_option
@verbose_option
@click.pass_context
def stop(ctx, system, force, dry_run, verbose):
    """Stop a system.
    
    \b
    Examples:
        tribench sys stop trino
        tribench sys stop all --force
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Stopping system: {system}")
        if force:
            click.echo("Force stop enabled")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would stop {system}")
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


@system_group.command(name="status")
@click.argument("system", 
                type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']),
                required=False)
@verbose_option
@click.pass_context
def status(ctx, system, verbose):
    """Check system status.
    
    \b
    Examples:
        tribench sys status
        tribench sys status trino
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if system:
        if ctx.obj.verbose:
            click.echo(f"Checking status of system: {system}")
    else:
        if ctx.obj.verbose:
            click.echo("Checking status of all systems")
        system = "all"
    
    # Implement system status check
    systems_to_check = ['trino', 'postgresql', 'minio', 'hive-metastore'] if system == 'all' else [system]
    
    for sys_name in systems_to_check:
        if sys_name == 'trino':
            try:
                trino = TrinoSystem()
                status_info = trino.status()
                
                if status_info['running']:
                    click.secho(f"✓ Trino: Running", fg='green')
                    if status_info.get('healthy'):
                        click.echo(f"  Health: OK")
                    if status_info.get('http_port'):
                        click.echo(f"  HTTP Port: {status_info['http_port']}")
                    if status_info.get('endpoint'):
                        click.echo(f"  Endpoint: {status_info['endpoint']}")
                else:
                    click.secho(f"✗ Trino: Not running", fg='yellow')
            except Exception as e:
                click.secho(f"✗ Failed to check Trino status: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'postgresql':
            try:
                postgresql = PostgreSQLSystem()
                status_info = postgresql.status()
                
                if status_info['running']:
                    click.secho(f"✓ PostgreSQL: Running", fg='green')
                    if status_info.get('healthy'):
                        click.echo(f"  Health: OK")
                    if status_info.get('port'):
                        click.echo(f"  Port: {status_info['port']}")
                    if status_info.get('databases'):
                        click.echo(f"  Databases: {', '.join(status_info['databases'])}")
                else:
                    click.secho(f"✗ PostgreSQL: Not running", fg='yellow')
            except Exception as e:
                click.secho(f"✗ Failed to check PostgreSQL status: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'minio':
            try:
                minio = MinIOSystem()
                status_info = minio.status()
                
                if status_info['running']:
                    click.secho(f"✓ MinIO: Running", fg='green')
                    if status_info.get('healthy'):
                        click.echo(f"  Health: OK")
                    if status_info.get('api_port'):
                        click.echo(f"  API Port: {status_info['api_port']}")
                    if status_info.get('console_port'):
                        click.echo(f"  Console Port: {status_info['console_port']}")
                    if status_info.get('endpoint'):
                        click.echo(f"  Endpoint: {status_info['endpoint']}")
                else:
                    click.secho(f"✗ MinIO: Not running", fg='yellow')
            except Exception as e:
                click.secho(f"✗ Failed to check MinIO status: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'hive-metastore':
            try:
                hive_metastore = HiveMetastoreSystem()
                status_info = hive_metastore.status()
                
                if status_info['running']:
                    click.secho(f"✓ Hive Metastore: Running", fg='green')
                    if status_info.get('healthy'):
                        click.echo(f"  Health: OK")
                    if status_info.get('port'):
                        click.echo(f"  Thrift Port: {status_info['port']}")
                    if status_info.get('warehouse'):
                        click.echo(f"  Warehouse: {status_info['warehouse']}")
                else:
                    click.secho(f"✗ Hive Metastore: Not running", fg='yellow')
            except Exception as e:
                click.secho(f"✗ Failed to check Hive Metastore status: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()


@system_group.command(name="teardown")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']))
@click.option('--keep-data', is_flag=True, help='Keep data after teardown.')
@click.confirmation_option(prompt='Are you sure you want to tear down the system?')
@dry_run_option
@verbose_option
@click.pass_context
def teardown(ctx, system, keep_data, dry_run, verbose):
    """Tear down a system (destructive operation).
    
    \b
    Examples:
        tribench sys teardown trino
        tribench sys teardown all --keep-data
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Tearing down system: {system}")
        if keep_data:
            click.echo("Will keep data after teardown")
    
    if ctx.obj.dry_run:
        click.echo(f"[DRY RUN] Would teardown {system}")
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


@system_group.command(name="logs")
@click.argument("system", type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore']))
@click.option('--tail', type=int, default=100, help='Number of lines to show from the end.')
@click.option('--follow', '-f', is_flag=True, help='Follow log output.')
@verbose_option
@click.pass_context
def logs(ctx, system, tail, follow, verbose):
    """Show system logs.
    
    \b
    Examples:
        tribench sys logs trino
        tribench sys logs trino --tail 50
        tribench sys logs trino --follow
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if ctx.obj.verbose:
        click.echo(f"Fetching logs for system: {system}")
    
    # Implement system logs
    if system == 'trino':
        try:
            trino = TrinoSystem()
            logs_output = trino.get_logs(tail=tail, follow=follow)
            click.echo(logs_output)
        except Exception as e:
            click.secho(f"✗ Failed to get Trino logs: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
    elif system == 'postgresql':
        try:
            postgresql = PostgreSQLSystem()
            logs_output = postgresql.get_logs(tail=tail, follow=follow)
            click.echo(logs_output)
        except Exception as e:
            click.secho(f"✗ Failed to get PostgreSQL logs: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
    elif system == 'minio':
        try:
            minio = MinIOSystem()
            logs_output = minio.get_logs(tail=tail, follow=follow)
            click.echo(logs_output)
        except Exception as e:
            click.secho(f"✗ Failed to get MinIO logs: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
    elif system == 'hive-metastore':
        try:
            hive_metastore = HiveMetastoreSystem()
            logs_output = hive_metastore.get_logs(tail=tail, follow=follow)
            click.echo(logs_output)
        except Exception as e:
            click.secho(f"✗ Failed to get Hive Metastore logs: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
