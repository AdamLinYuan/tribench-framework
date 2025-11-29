"""Base CLI setup for TriBench using Click."""

import click
import sys
from pathlib import Path
from tribench.__version__ import __version__


# Common options that can be reused across commands
def dry_run_option(f):
    """Decorator for adding --dry-run option."""
    return click.option(
        '--dry-run',
        is_flag=True,
        help='Show what would be done without executing.'
    )(f)


def verbose_option(f):
    """Decorator for adding --verbose option."""
    return click.option(
        '-v', '--verbose',
        is_flag=True,
        help='Enable verbose output.'
    )(f)


def config_option(f):
    """Decorator for adding --config option."""
    return click.option(
        '-c', '--config',
        type=click.Path(exists=True),
        help='Path to configuration file.'
    )(f)


def kind_option(f):
    """Decorator for adding --kind option for Kubernetes deployments."""
    return click.option(
        '--kind',
        is_flag=True,
        help='Use Kubernetes backend (ensures port forwarding is active).'
    )(f)


def is_k8s_deployment_active() -> bool:
    """
    Check if Kubernetes deployment is active by looking for:
    1. Port forwarding PID file exists
    2. Port 8080 is accessible
    
    Returns:
        True if K8s deployment appears to be active
    """
    pid_file = Path("log/port-forward.pid")
    if pid_file.exists():
        return True
    
    # Also check if port 8080 is accessible (might be manually forwarded)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('localhost', 8080))
        sock.close()
        return result == 0
    except Exception:
        return False


def ensure_k8s_port_forwarding(config=None, echo=click.echo, silent_if_active=False) -> bool:
    """
    Ensure Kubernetes port forwarding is active for Trino access.
    
    Args:
        config: Optional configuration dictionary
        echo: Function to use for output (default: click.echo)
        silent_if_active: If True, don't print anything if already active
    
    Returns:
        True if port forwarding is now active, False otherwise
    """
    from tribench.systems.kubernetes_system import KubernetesSystem
    
    k8s_config = {
        "context": "kind-tribench",
        "namespace": "tribench",
        "local_port": 8080,
        "container_port": 8080,
        "config_tree": config
    }
    k8s = KubernetesSystem("k8s-system", k8s_config)
    
    # Check if already active
    if k8s.is_port_forwarding_active():
        if not silent_if_active:
            click.secho("✓ Port forwarding already active", fg='green')
        return True
    
    echo("Kubernetes mode: starting port forwarding...")
    
    if not k8s.ensure_port_forwarding():
        click.secho("✗ Failed to establish port forwarding. Is Trino running in Kubernetes?", fg='red')
        click.echo("  Try: tribench sys start trino --kind")
        return False
    
    click.secho("✓ Port forwarding active", fg='green')
    return True


def auto_ensure_trino_connection(config=None) -> bool:
    """
    Automatically ensure Trino is accessible.
    
    For Kubernetes deployments (detected via PID file), ensures port forwarding.
    For Docker deployments, just checks if Trino is reachable.
    
    Returns:
        True if Trino should be accessible, False otherwise
    """
    import socket
    
    # First check if Trino is already accessible
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 8080))
        sock.close()
        if result == 0:
            return True  # Trino is accessible
    except Exception:
        pass
    
    # Check if this looks like a K8s deployment (PID file exists)
    pid_file = Path("log/port-forward.pid")
    if pid_file.exists():
        # K8s deployment but port forwarding died - try to restart
        click.echo("Port forwarding appears to have stopped. Restarting...")
        return ensure_k8s_port_forwarding(config, silent_if_active=True)
    
    # Not accessible and no K8s indicators - let the command fail naturally
    return True


class TriBenchContext:
    """Context object for passing state between commands."""
    
    def __init__(self):
        self.verbose = False
        self.dry_run = False
        self.config_path = None
        self.root_dir = Path(__file__).parent.parent.parent.parent


@click.group()
@click.version_option(version=__version__, prog_name="TriBench")
@verbose_option
@click.pass_context
def cli(ctx, verbose):
    """
    TriBench - Trino Benchmarking Framework
    
    A systematic, reproducible framework for benchmarking SQL workloads
    on distributed data lakehouses using Apache Trino.
    
    \b
    Examples:
        tribench sys setup trino
        tribench exp run experiments/tpch-sf1.yaml
        tribench res show exp-001
    """
    ctx.ensure_object(TriBenchContext)
    ctx.obj.verbose = verbose
    
    if verbose:
        click.echo(f"TriBench v{__version__}", err=True)


@cli.command()
def version():
    """Show detailed version information."""
    click.echo(f"TriBench version {__version__}")
    click.echo("A PEEL-inspired benchmarking framework for Trino")
    click.echo(f"Python: {sys.version.split()[0]}")
    click.echo(f"Platform: {sys.platform}")


if __name__ == "__main__":
    cli()