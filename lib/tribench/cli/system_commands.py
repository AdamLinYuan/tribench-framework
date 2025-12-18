"""System management commands."""

import click
from pathlib import Path
from tribench.cli.base import cli, dry_run_option, verbose_option, config_option
from tribench.systems.trino import TrinoSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.systems.kubernetes_system import KubernetesSystem
from tribench.utils.config import ConfigurationLoader
from tribench.defaults import Defaults


@cli.group(name="sys")
def system_group():
    """System lifecycle management commands.
    
    Manage Trino, PostgreSQL, MinIO and other system components.
    """
    pass


def get_k8s_system(config_tree=None):
    """Get configured KubernetesSystem instance."""
    # Try to detect context or use default
    context = Defaults.Kubernetes.CONTEXT
    
    # Check if context is defined in config
    if config_tree:
        context = config_tree.get("kubernetes.context", None)

    if not context:
        context = Defaults.Kubernetes.CONTEXT
        try:
            import subprocess
            # Check available contexts
            result = subprocess.run(["kubectl", "config", "get-contexts", "-o", "name"], capture_output=True, text=True)
            contexts = result.stdout.strip().split('\n')
            
            # Prioritize kind-tribench
            if Defaults.Kubernetes.CONTEXT in contexts:
                context = Defaults.Kubernetes.CONTEXT
            elif "docker-desktop" in contexts:
                context = "docker-desktop"
            # If neither, stick to default or maybe first available?
        except Exception:
            pass

    config = {
        "context": context,
        "namespace": Defaults.Kubernetes.NAMESPACE,
        "helm_chart": "trinodb/trino",
        "helm_release": Defaults.ServiceNames.TRINO,
        "minio_chart": "minio/minio",
        "minio_release": Defaults.ServiceNames.MINIO,
        "local_port": Defaults.Trino.PORT,
        "container_port": Defaults.Trino.PORT,
        "timeout": 600,
        "config_tree": config_tree,
        "kind_config": "config/kubernetes/kind-config.yaml",
    }
    return KubernetesSystem("k8s-system", config)


@system_group.command(name="setup")
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


@system_group.command(name="start")
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


@system_group.command(name="stop")
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


@system_group.command(name="status")
@click.argument("system", 
                type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']),
                required=False)
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
@verbose_option
@click.pass_context
def status(ctx, system, kind, verbose):
    """Check system status.
    
    \b
    Examples:
        tribench sys status
        tribench sys status trino
        tribench sys status --kind
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    if system:
        if ctx.obj.verbose:
            click.echo(f"Checking status of system: {system}")
    else:
        if ctx.obj.verbose:
            click.echo("Checking status of all systems")
        system = "all"
    
    if kind:
        try:
            k8s = get_k8s_system()
            status_info = k8s.status()
            
            if status_info.get('error'):
                click.secho(f"✗ Kubernetes Status Error: {status_info['error']}", fg='red')
            else:
                click.secho("Kubernetes System Status:", fg='blue', bold=True)
                click.echo(f"  Running: {status_info['running']}")
                
                click.echo("  Pods:")
                for pod in status_info.get('pods', []):
                    status_color = 'green' if pod['status'] == 'Running' and pod['ready'] else 'yellow'
                    click.secho(f"    - {pod['name']}: {pod['status']} (Ready: {pod['ready']})", fg=status_color)
                
                click.echo("  Services:")
                for svc in status_info.get('services', []):
                    click.echo(f"    - {svc['name']} ({svc['type']})")
        except Exception as e:
            click.secho(f"✗ Failed to check Kubernetes status: {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                traceback.print_exc()
        return

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


@system_group.command(name="port-forward")
@click.argument("action", type=click.Choice(['start', 'stop', 'status']))
@click.option('--port', type=int, default=Defaults.Trino.PORT, help=f'Local port to forward (default: {Defaults.Trino.PORT}).')
@verbose_option
@click.pass_context
def port_forward(ctx, action, port, verbose):
    """Manage Kubernetes port forwarding for Trino access.
    
    Port forwarding allows local access to Trino running in Kubernetes.
    Once started, it persists until explicitly stopped or the process is killed.
    
    \b
    Examples:
        tribench sys port-forward start     # Start port forwarding
        tribench sys port-forward status    # Check if port forwarding is active
        tribench sys port-forward stop      # Stop port forwarding
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    try:
        k8s = get_k8s_system()
        k8s.local_port = port
        k8s.container_port = port
        
        if action == 'start':
            click.echo(f"Starting port forwarding on port {port}...")
            
            # Check if Trino is running first
            status = k8s.status()
            if not status.get("running"):
                click.secho("✗ Trino is not running in Kubernetes.", fg='red')
                click.echo("  Start it first with: tribench sys start trino --kind")
                return
            
            k8s.start_port_forwarding()
            
            if k8s.is_port_forwarding_active():
                click.secho(f"✓ Port forwarding active on localhost:{port}", fg='green')
                click.echo(f"  Trino is now accessible at http://{Defaults.Hosts.LOCALHOST}:{Defaults.Trino.PORT}")
                click.echo("  Stop with: tribench sys port-forward stop")
            else:
                click.secho("✗ Failed to start port forwarding", fg='red')
                click.echo("  Check log/port-forward.log for details")
                
        elif action == 'stop':
            click.echo("Stopping port forwarding...")
            k8s.stop_port_forwarding()
            click.secho("✓ Port forwarding stopped", fg='green')
            
        elif action == 'status':
            if k8s.is_port_forwarding_active():
                # Try to get PID from file
                from pathlib import Path
                pid_file = Path("log/port-forward.pid")
                pid_info = ""
                if pid_file.exists():
                    try:
                        pid = pid_file.read_text().strip()
                        pid_info = f" (pid {pid})"
                    except:
                        pass
                click.secho(f"✓ Port forwarding is active on localhost:{port}{pid_info}", fg='green')
            else:
                click.secho(f"✗ Port forwarding is not active", fg='yellow')
                click.echo("  Start with: tribench sys port-forward start")
                
    except Exception as e:
        click.secho(f"✗ Port forward operation failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()


@system_group.command(name="cluster")
@click.argument("action", type=click.Choice(['create', 'delete', 'status', 'recreate']))
@click.option('--config', '-c', 'kind_config', 
              type=click.Path(exists=True),
              default='config/kubernetes/kind-config.yaml',
              help='Kind cluster configuration file.')
@click.option('--force', '-f', is_flag=True, help='Force operation (e.g., delete existing cluster before create).')
@dry_run_option
@verbose_option
@click.pass_context
def cluster(ctx, action, kind_config, force, dry_run, verbose):
    """Manage the Kind Kubernetes cluster.
    
    This command manages the Kind cluster lifecycle using the configuration
    specified in config/kubernetes/kind-config.yaml (or custom path).
    
    The configuration file defines the number of control-plane and worker nodes.
    
    \b
    Actions:
        create   - Create a new Kind cluster with the specified config
        delete   - Delete the Kind cluster
        status   - Show cluster status and compare with config
        recreate - Delete and recreate the cluster (same as delete + create)
    
    \b
    Examples:
        tribench sys cluster status                    # Check cluster status
        tribench sys cluster create                    # Create cluster from config
        tribench sys cluster create --force            # Recreate if exists
        tribench sys cluster recreate                  # Delete and recreate
        tribench sys cluster delete                    # Delete cluster
        tribench sys cluster create -c my-config.yaml  # Use custom config
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    try:
        k8s = get_k8s_system()
        k8s.kind_config = Path(kind_config)
        
        if action == 'status':
            click.echo("Checking Kind cluster status...")
            status = k8s.cluster_status()
            
            click.echo(f"\nCluster: {status['cluster_name']}")
            click.echo(f"Config file: {status['config_file']}")
            
            if not status['exists']:
                click.secho("Status: Not created", fg='yellow')
                click.echo("\nTo create the cluster:")
                click.echo("  tribench sys cluster create")
            else:
                if status['running']:
                    click.secho("Status: Running", fg='green')
                else:
                    click.secho("Status: Not ready", fg='yellow')
                
                # Show nodes
                click.echo("\nNodes:")
                for node in status.get('nodes', []):
                    ready_icon = "✓" if node['ready'] else "○"
                    ready_color = 'green' if node['ready'] else 'yellow'
                    click.secho(f"  {ready_icon} {node['name']} ({node['role']})", fg=ready_color)
                
                # Show expected config
                expected = status.get('expected_nodes', {})
                if expected:
                    click.echo(f"\nExpected from config:")
                    click.echo(f"  Control-plane nodes: {expected.get('control-plane', 0)}")
                    click.echo(f"  Worker nodes: {expected.get('worker', 0)}")
                    
                    if status.get('config_matches'):
                        click.secho("\n✓ Cluster matches configuration", fg='green')
                    else:
                        click.secho("\n⚠ Cluster does NOT match configuration", fg='yellow')
                        click.echo("  To fix, recreate the cluster:")
                        click.echo("  tribench sys cluster recreate")
        
        elif action == 'create':
            if ctx.obj.dry_run:
                click.echo(f"[DRY RUN] Would create Kind cluster from {kind_config}")
                return
            
            click.echo(f"Creating Kind cluster from {kind_config}...")
            
            if k8s.cluster_exists() and not force:
                click.secho(f"✗ Cluster '{k8s.cluster_name}' already exists.", fg='yellow')
                click.echo("  Use --force to delete and recreate")
                click.echo("  Or use 'tribench sys cluster status' to check current state")
                return
            
            k8s.create_cluster(force=force)
            click.secho(f"✓ Kind cluster created successfully", fg='green')
            
            # Show status
            status = k8s.cluster_status()
            click.echo(f"\nCluster nodes:")
            for node in status.get('nodes', []):
                click.secho(f"  ✓ {node['name']} ({node['role']})", fg='green')
            
            click.echo("\nNext steps:")
            click.echo("  1. Setup and start systems: tribench sys setup all --kind")
            click.echo("  2. Or start existing: tribench sys start all --kind")
        
        elif action == 'delete':
            if ctx.obj.dry_run:
                click.echo(f"[DRY RUN] Would delete Kind cluster '{k8s.cluster_name}'")
                return
            
            if not k8s.cluster_exists():
                click.secho(f"Cluster '{k8s.cluster_name}' does not exist", fg='yellow')
                return
            
            if not force:
                if not click.confirm(f"Delete Kind cluster '{k8s.cluster_name}'? This will destroy all data."):
                    click.echo("Cancelled")
                    return
            
            click.echo(f"Deleting Kind cluster '{k8s.cluster_name}'...")
            k8s.delete_cluster()
            click.secho(f"✓ Kind cluster deleted", fg='green')
        
        elif action == 'recreate':
            if ctx.obj.dry_run:
                click.echo(f"[DRY RUN] Would recreate Kind cluster from {kind_config}")
                return
            
            if not force:
                if not click.confirm(f"Recreate Kind cluster? This will destroy all data."):
                    click.echo("Cancelled")
                    return
            
            click.echo(f"Recreating Kind cluster from {kind_config}...")
            
            if k8s.cluster_exists():
                click.echo("Deleting existing cluster...")
                k8s.delete_cluster()
            
            click.echo("Creating new cluster...")
            k8s.create_cluster()
            click.secho(f"✓ Kind cluster recreated successfully", fg='green')
            
            # Show status
            status = k8s.cluster_status()
            click.echo(f"\nCluster nodes:")
            for node in status.get('nodes', []):
                click.secho(f"  ✓ {node['name']} ({node['role']})", fg='green')
                
    except FileNotFoundError as e:
        click.secho(f"✗ {e}", fg='red')
    except Exception as e:
        click.secho(f"✗ Cluster operation failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()
