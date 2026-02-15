"""
Kubernetes-specific commands.

Commands for managing Kubernetes clusters and port forwarding.
"""

import click
from pathlib import Path
from tribench.cli.base import dry_run_option, verbose_option, config_option
from tribench.defaults import Defaults
from tribench.utils.config import ConfigurationLoader
from .utils import get_k8s_system


@click.command(name="port-forward")
@click.argument("action", type=click.Choice(['start', 'stop', 'status']))
@click.option('--port', type=int, default=Defaults.Trino.PORT, help=f'Local port to forward (default: {Defaults.Trino.PORT}).')
@config_option
@verbose_option
@click.pass_context
def port_forward(ctx, action, port, config, verbose):
    """Manage Kubernetes port forwarding for Trino and MinIO access.
    
    Port forwarding allows local access to services running in Kubernetes.
    This command forwards both Trino (8080) and MinIO (9000/9001) ports.
    Once started, it persists until explicitly stopped or the process is killed.
    
    \b
    Examples:
        tribench sys port-forward start     # Start port forwarding (Trino + MinIO)
        tribench sys port-forward status    # Check if port forwarding is active
        tribench sys port-forward stop      # Stop port forwarding
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Load configuration (respects active profile)
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config) if config else config_loader.load()
    
    try:
        k8s = get_k8s_system(config_tree=full_config)
        k8s.local_port = port
        k8s.container_port = port
        
        if action == 'start':
            click.echo("Starting port forwarding...")
            
            # Check if Trino is running first
            status = k8s.status()
            if not status.get("running"):
                click.secho("✗ Trino is not running in Kubernetes.", fg='red')
                click.echo("  Start it first with: tribench sys start trino")
                return
            
            # Start both Trino and MinIO port forwards
            k8s.start_port_forwarding(include_minio=True)
            
            # Check status
            trino_active = k8s.is_port_forwarding_active()
            minio_active = k8s.is_minio_port_forwarding_active()
            
            if trino_active and minio_active:
                click.secho("✓ Port forwarding active", fg='green')
                click.echo(f"  Trino:  http://{Defaults.Hosts.LOCALHOST}:{Defaults.Trino.PORT}")
                click.echo(f"  MinIO:  http://{Defaults.Hosts.LOCALHOST}:{Defaults.MinIO.PORT} (API)")
                click.echo(f"          http://{Defaults.Hosts.LOCALHOST}:{Defaults.MinIO.CONSOLE_PORT} (Console)")
                click.echo("")
                click.echo("  Stop with: tribench sys port-forward stop")
            elif trino_active:
                click.secho("⚠ Trino port forwarding active, but MinIO failed", fg='yellow')
                click.echo(f"  Trino: http://{Defaults.Hosts.LOCALHOST}:{Defaults.Trino.PORT}")
                click.echo("  Check log/port-forward-minio.log for details")
            else:
                click.secho("✗ Failed to start port forwarding", fg='red')
                click.echo("  Check log/port-forward.log for details")
                
        elif action == 'stop':
            click.echo("Stopping port forwarding...")
            k8s.stop_port_forwarding()
            click.secho("✓ Port forwarding stopped", fg='green')
            
        elif action == 'status':
            trino_active = k8s.is_port_forwarding_active()
            minio_active = k8s.is_minio_port_forwarding_active()
            
            if trino_active and minio_active:
                click.secho("✓ Port forwarding is active", fg='green')
                click.echo(f"  Trino:  localhost:{Defaults.Trino.PORT}")
                click.echo(f"  MinIO:  localhost:{Defaults.MinIO.PORT} (API)")
                click.echo(f"          localhost:{Defaults.MinIO.CONSOLE_PORT} (Console)")
            elif trino_active:
                click.secho("⚠ Trino active, MinIO not active", fg='yellow')
                click.echo(f"  Trino:  localhost:{Defaults.Trino.PORT}")
            elif minio_active:
                click.secho("⚠ MinIO active, Trino not active", fg='yellow')
                click.echo(f"  MinIO:  localhost:{Defaults.MinIO.PORT}")
            else:
                click.secho("✗ Port forwarding is not active", fg='yellow')
                click.echo("  Start with: tribench sys port-forward start")
                
    except Exception as e:
        click.secho(f"✗ Port forward operation failed: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            traceback.print_exc()


@click.command(name="cluster")
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
            
            # Install metrics-server for monitoring
            click.echo("\nInstalling metrics-server for pod monitoring...")
            try:
                if k8s.install_metrics_server():
                    click.secho("✓ metrics-server installed", fg='green')
                else:
                    click.secho("⚠ metrics-server installation may have failed", fg='yellow')
            except Exception as e:
                click.secho(f"⚠ Failed to install metrics-server: {e}", fg='yellow')
                click.echo("  You can install it later with: kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml")
            
            # Show status
            status = k8s.cluster_status()
            click.echo(f"\nCluster nodes:")
            for node in status.get('nodes', []):
                click.secho(f"  ✓ {node['name']} ({node['role']})", fg='green')
            
            click.echo("\nNext steps:")
            click.echo("  1. Setup and start systems: tribench sys setup all")
            click.echo("  2. Or start existing: tribench sys start all")
        
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
            
            # Install metrics-server for monitoring
            click.echo("\nInstalling metrics-server for pod monitoring...")
            try:
                if k8s.install_metrics_server():
                    click.secho("✓ metrics-server installed", fg='green')
                else:
                    click.secho("⚠ metrics-server installation may have failed", fg='yellow')
            except Exception as e:
                click.secho(f"⚠ Failed to install metrics-server: {e}", fg='yellow')
            
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
