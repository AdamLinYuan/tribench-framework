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


def _load_cfg(ctx, config_path=None):
    """Load config with bundle_root taken from Click context if available."""
    bundle_root = getattr(ctx.obj, 'bundle_root', None)
    loader = ConfigurationLoader(bundle_root=bundle_root)
    return loader.load(experiment_config=config_path) if config_path else loader.load()


@click.command(name="status")
@click.argument("system", 
                type=click.Choice(['trino', 'postgresql', 'minio', 'hive-metastore', 'all']),
                required=False)
@config_option
@verbose_option
@click.pass_context
def status(ctx, system, config, verbose):
    """Check system status.
    
    Backend selection is configured in host config files.
    Use 'tribench config profile <name>' to set your preferred backend.
    
    \b
    Examples:
        tribench sys status
        tribench sys status trino
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration first to check backend default
    cfg = _load_cfg(ctx, config)
    
    # Determine backend
    use_k8s = should_use_kubernetes(cfg)
    
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
                
                # Show context and namespace
                context = cfg.get('tribench.kubernetes.context', 'default')
                namespace = cfg.get('tribench.kubernetes.namespace', 'default')
                click.echo(f"  Context: {context}")
                click.echo(f"  Namespace: {namespace}")
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
    
    # Calculate running status first
    any_running = False
    status_results = {}
    
    # Pre-check all systems
    for sys_name in systems_to_check:
        try:
            if sys_name == 'trino':
                trino = TrinoSystem()
                status_results[sys_name] = trino.status()
            elif sys_name == 'postgresql':
                postgresql = PostgreSQLSystem()
                status_results[sys_name] = postgresql.status()
            elif sys_name == 'minio':
                minio = MinIOSystem()
                status_results[sys_name] = minio.status()
            elif sys_name == 'hive-metastore':
                hive_metastore = HiveMetastoreSystem()
                status_results[sys_name] = hive_metastore.status()
            
            if status_results.get(sys_name, {}).get('running'):
                any_running = True
        except Exception:
            status_results[sys_name] = {'running': False, 'error': True}
    
    # Docker status with consistent format
    click.secho("Docker System Status:", fg='blue', bold=True)
    click.echo(f"  Backend: docker-compose")
    click.echo(f"  Running: {any_running}")
    
    for sys_name in systems_to_check:
        status_info = status_results.get(sys_name, {})
        
        if sys_name == 'trino':
            try:
                if status_info.get('running'):
                    click.secho(f"\n  Trino:", fg='green', bold=True)
                    click.echo(f"    Status: Running")
                    if status_info.get('healthy'):
                        click.echo(f"    Health: OK")
                    if status_info.get('http_port'):
                        click.echo(f"    HTTP Port: {status_info['http_port']}")
                    if status_info.get('endpoint'):
                        click.echo(f"    Endpoint: {status_info['endpoint']}")
                    
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
                            click.secho(f"    ⚠ Could not retrieve worker statistics: {e}", fg='yellow')
                else:
                    click.secho(f"\n  Trino:", fg='yellow', bold=True)
                    click.echo(f"    Status: Not running")
            except Exception as e:
                click.secho(f"\n  Trino:", fg='red', bold=True)
                click.echo(f"    Status: Error - {e}")
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'postgresql':
            try:
                if status_info.get('running'):
                    click.secho(f"\n  PostgreSQL:", fg='green', bold=True)
                    click.echo(f"    Status: Running")
                    if status_info.get('healthy'):
                        click.echo(f"    Health: OK")
                    if status_info.get('port'):
                        click.echo(f"    Port: {status_info['port']}")
                    if status_info.get('databases'):
                        click.echo(f"    Databases: {', '.join(status_info['databases'])}")
                else:
                    click.secho(f"\n  PostgreSQL:", fg='yellow', bold=True)
                    click.echo(f"    Status: Not running")
            except Exception as e:
                click.secho(f"\n  PostgreSQL:", fg='red', bold=True)
                click.echo(f"    Status: Error - {e}")
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'minio':
            try:
                if status_info.get('running'):
                    click.secho(f"\n  MinIO:", fg='green', bold=True)
                    click.echo(f"    Status: Running")
                    if status_info.get('healthy'):
                        click.echo(f"    Health: OK")
                    if status_info.get('api_port'):
                        click.echo(f"    API Port: {status_info['api_port']}")
                    if status_info.get('console_port'):
                        click.echo(f"    Console Port: {status_info['console_port']}")
                    if status_info.get('endpoint'):
                        click.echo(f"    Endpoint: {status_info['endpoint']}")
                else:
                    click.secho(f"\n  MinIO:", fg='yellow', bold=True)
                    click.echo(f"    Status: Not running")
            except Exception as e:
                click.secho(f"\n  MinIO:", fg='red', bold=True)
                click.echo(f"    Status: Error - {e}")
                if ctx.obj.verbose:
                    import traceback
                    traceback.print_exc()
        elif sys_name == 'hive-metastore':
            try:
                if status_info.get('running'):
                    click.secho(f"\n  Hive Metastore:", fg='green', bold=True)
                    click.echo(f"    Status: Running")
                    if status_info.get('healthy'):
                        click.echo(f"    Health: OK")
                    if status_info.get('port'):
                        click.echo(f"    Thrift Port: {status_info['port']}")
                    if status_info.get('warehouse'):
                        click.echo(f"    Warehouse: {status_info['warehouse']}")
                else:
                    click.secho(f"\n  Hive Metastore:", fg='yellow', bold=True)
                    click.echo(f"    Status: Not running")
            except Exception as e:
                click.secho(f"\n  Hive Metastore:", fg='red', bold=True)
                click.echo(f"    Status: Error - {e}")
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
