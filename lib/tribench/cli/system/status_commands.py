"""
System status commands.

Commands for checking system status and viewing logs.
"""

import click
from tribench.cli.base import verbose_option, config_option, should_use_kubernetes
from tribench.systems.trino import TrinoSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.utils.config import ConfigurationLoader
from .utils import get_k8s_system


@click.command(name="status")
@click.argument("system", 
                type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']),
                required=False)
@click.option('--kind', is_flag=True, help='Use Kubernetes backend (Kind/Helm).')
@config_option
@verbose_option
@click.pass_context
def status(ctx, system, kind, config, verbose):
    """Check system status.
    
    \b
    Examples:
        tribench sys status
        tribench sys status trino
        tribench sys status --kind
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration first to check backend default
    loader = ConfigurationLoader()
    cfg = loader.load(experiment_config=config) if config else loader.load()
    
    # Determine backend
    use_k8s = should_use_kubernetes(kind, cfg)
    
    if system:
        if ctx.obj.verbose:
            click.echo(f"Checking status of system: {system}")
    else:
        if ctx.obj.verbose:
            click.echo("Checking status of all systems")
        system = "all"
    
    if use_k8s:
        try:
            k8s = get_k8s_system(config_tree=cfg)
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
                
                # Get Trino worker statistics if Trino is running
                trino_running = any(p['name'].startswith('trino-') and p['status'] == 'Running' for p in status_info.get('pods', []))
                if trino_running:
                    try:
                        from tribench.monitoring.trino.api_client import TrinoAPIClient
                        
                        # Use localhost with port forwarding
                        coordinator_url = 'http://localhost:8080'
                        api_client = TrinoAPIClient(base_url=coordinator_url, user='tribench')
                        
                        # Get worker information
                        workers = api_client.get_worker_info()
                        if workers:
                            click.echo(f"\n  Trino Workers ({len(workers)} nodes):")
                            for worker in workers:
                                node_type = "Coordinator" if worker.get('coordinator') else "Worker"
                                state = worker.get('state', 'UNKNOWN')
                                state_color = 'green' if state == 'ACTIVE' else 'yellow'
                                
                                node_id = worker.get('node_id', 'unknown')[:20]
                                click.echo(f"    - {node_id} ({node_type}):")
                                click.secho(f"        State: {state}", fg=state_color)
                                
                                if worker.get('uri'):
                                    click.echo(f"        URI: {worker['uri']}")
                                
                                # Memory information
                                memory_info = worker.get('memory', {})
                                if memory_info:
                                    total_mb = (memory_info.get('total_bytes') or 0) / (1024 * 1024)
                                    available_mb = (memory_info.get('available_bytes') or 0) / (1024 * 1024)
                                    used_mb = total_mb - available_mb
                                    
                                    if total_mb > 0:
                                        usage_pct = (used_mb / total_mb) * 100
                                        click.echo(f"        Memory: {used_mb:.2f} MB / {total_mb:.2f} MB ({usage_pct:.1f}% used)")
                                    
                                    # Show memory pools if available
                                    for key, value in memory_info.items():
                                        if '_reserved_bytes' in key and value:
                                            pool_name = key.replace('_reserved_bytes', '')
                                            reserved_mb = value / (1024 * 1024)
                                            click.echo(f"        {pool_name.title()} Pool Reserved: {reserved_mb:.2f} MB")
                                
                                # Request statistics
                                recent_requests = worker.get('recent_requests')
                                recent_failures = worker.get('recent_failures')
                                if recent_requests is not None:
                                    failure_rate = (recent_failures / recent_requests * 100) if recent_requests > 0 else 0
                                    click.echo(f"        Recent Requests: {recent_requests} (Failures: {recent_failures}, {failure_rate:.1f}%)")
                        else:
                            if ctx.obj.verbose:
                                click.secho(f"  ⚠ Worker information not available (may need port forwarding)", fg='yellow')
                    except Exception as e:
                        if ctx.obj.verbose:
                            click.secho(f"  ⚠ Could not retrieve Trino worker statistics: {e}", fg='yellow')
                            click.echo(f"  Hint: Make sure port forwarding is active: tribench sys port-forward start")
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
                    
                    # Get worker statistics via API
                    try:
                        from tribench.monitoring.trino.api_client import TrinoAPIClient
                        
                        # Try to get endpoint from status or use default
                        coordinator_url = status_info.get('endpoint') or 'http://localhost:8080'
                        api_client = TrinoAPIClient(base_url=coordinator_url, user='tribench')
                        
                        # Get worker information
                        workers = api_client.get_worker_info()
                        if workers:
                            click.echo(f"\n  Workers ({len(workers)} nodes):")
                            for worker in workers:
                                node_type = "Coordinator" if worker.get('coordinator') else "Worker"
                                state = worker.get('state', 'UNKNOWN')
                                state_color = 'green' if state == 'ACTIVE' else 'yellow'
                                
                                node_id = worker.get('node_id', 'unknown')[:20]
                                click.echo(f"    - {node_id} ({node_type}):")
                                click.secho(f"        State: {state}", fg=state_color)
                                
                                if worker.get('uri'):
                                    click.echo(f"        URI: {worker['uri']}")
                                
                                # Memory information
                                memory_info = worker.get('memory', {})
                                if memory_info:
                                    total_mb = (memory_info.get('total_bytes') or 0) / (1024 * 1024)
                                    available_mb = (memory_info.get('available_bytes') or 0) / (1024 * 1024)
                                    used_mb = total_mb - available_mb
                                    
                                    if total_mb > 0:
                                        usage_pct = (used_mb / total_mb) * 100
                                        click.echo(f"        Memory: {used_mb:.2f} MB / {total_mb:.2f} MB ({usage_pct:.1f}% used)")
                                    
                                    # Show memory pools if available
                                    for key, value in memory_info.items():
                                        if '_reserved_bytes' in key and value:
                                            pool_name = key.replace('_reserved_bytes', '')
                                            reserved_mb = value / (1024 * 1024)
                                            click.echo(f"        {pool_name.title()} Pool Reserved: {reserved_mb:.2f} MB")
                                
                                # Request statistics
                                recent_requests = worker.get('recent_requests')
                                recent_failures = worker.get('recent_failures')
                                if recent_requests is not None:
                                    failure_rate = (recent_failures / recent_requests * 100) if recent_requests > 0 else 0
                                    click.echo(f"        Recent Requests: {recent_requests} (Failures: {recent_failures}, {failure_rate:.1f}%)")
                        
                    except Exception as e:
                        if ctx.obj.verbose:
                            click.secho(f"  ⚠ Could not retrieve worker statistics: {e}", fg='yellow')
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


@click.command(name="logs")
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
