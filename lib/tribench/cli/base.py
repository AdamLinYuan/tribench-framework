"""Base CLI setup for TriBench using Click."""

import click
import sys
from pathlib import Path
from tribench.__version__ import __version__
from tribench.defaults import Defaults


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


def should_use_kubernetes(config) -> bool:
    """
    Determine whether to use Kubernetes backend based on configuration.
    
    Args:
        config: Configuration tree (ConfigTree or dict)
    
    Returns:
        True if Kubernetes backend should be used, False for Docker Compose
    
    The backend is determined by the 'tribench.defaults.backend' configuration value.
    Set via 'tribench config profile <name>' or in host config files.
    
    Example:
        >>> # Config sets Kubernetes as default
        >>> config = {'tribench': {'defaults': {'backend': 'kubernetes'}}}
        >>> should_use_kubernetes(config=config)
        True
        
        >>> # Docker default in config
        >>> config = {'tribench': {'defaults': {'backend': 'docker'}}}
        >>> should_use_kubernetes(config=config)
        False
        
        >>> # No config defaults to Docker
        >>> should_use_kubernetes(config={})
        False
    """
    # Check configuration default
    try:
        if hasattr(config, 'get'):
            # ConfigTree object
            backend = config.get('tribench.defaults.backend', 'docker')
        elif isinstance(config, dict):
            # Plain dict
            backend = config.get('tribench', {}).get('defaults', {}).get('backend', 'docker')
        else:
            backend = 'docker'
        
        return backend == 'kubernetes'
    except Exception:
        # Fallback to Docker if config access fails
        return False


def is_k8s_deployment_active() -> bool:
    """
    Check if Kubernetes deployment is active by looking for:
    1. Port forwarding PID file exists
    2. Trino port is accessible
    
    Returns:
        True if K8s deployment appears to be active
    """
    pid_file = get_log_dir() / "port-forward.pid"
    if pid_file.exists():
        return True
    
    # Also check if Trino port is accessible (might be manually forwarded)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((Defaults.Hosts.LOCALHOST, Defaults.Trino.PORT))
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
    
    # Handle None config
    if config is None:
        config = {}
    
    # Pass config to use proper context hierarchy
    k8s_config = {
        "systems": config.get("systems", {}),  # Pass systems config
        "local_port": Defaults.Trino.PORT,
        "container_port": Defaults.Trino.PORT,
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
        click.echo("  Try: tribench sys start trino")
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
        result = sock.connect_ex((Defaults.Hosts.LOCALHOST, Defaults.Trino.PORT))
        sock.close()
        if result == 0:
            return True  # Trino is accessible
    except Exception:
        pass
    
    # Check if this looks like a K8s deployment (PID file exists)
    pid_file = get_log_dir() / "port-forward.pid"
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
        self.bundle_root: Path | None = None   # set by --bundle option

    @property
    def log_dir(self) -> Path:
        """Return the log directory: bundle's log/ when active, else CWD/log/."""
        if self.bundle_root is not None:
            return self.bundle_root / "log"
        return Path("log")


def get_log_dir(ctx_obj=None) -> Path:
    """Return the active log directory, falling back to CWD/log/ if no context."""
    if ctx_obj is not None and hasattr(ctx_obj, 'log_dir'):
        return ctx_obj.log_dir
    # Fallback: check active bundle state file
    try:
        from tribench.bundle.manifest import get_active_bundle
        active = get_active_bundle()
        if active and active.exists():
            return active / "log"
    except Exception:
        pass
    return Path("log")


@click.group()
@click.version_option(version=__version__, prog_name="TriBench")
@verbose_option
@click.option(
    '--bundle',
    default=None,
    envvar='TRIBENCH_BUNDLE',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help=(
        'Path to the bundle directory to use. '
        'Defaults to auto-detection (walks up from CWD looking for bundle.yaml). '
        'Can also be set via the TRIBENCH_BUNDLE environment variable.'
    ),
)
@click.pass_context
def cli(ctx, verbose, bundle):
    """
    TriBench - Trino Benchmarking Framework
    
    A systematic, reproducible framework for benchmarking SQL workloads
    on distributed data lakehouses using Apache Trino.
    
    \b
    Examples:
        tribench sys setup trino
        tribench exp run experiments/tpch-sf1.yaml
        tribench res show exp-001
        tribench --bundle /data/bundles/tpch exp run experiments/tpch-sf1.yaml
    """
    ctx.ensure_object(TriBenchContext)
    ctx.obj.verbose = verbose

    # Resolve bundle: --bundle flag > active-bundle state file > auto-detect
    resolved_bundle: Path | None = None
    if bundle:
        resolved_bundle = Path(bundle)
    else:
        from tribench.bundle.manifest import get_active_bundle
        active = get_active_bundle()
        if active and active.exists():
            resolved_bundle = active

    if resolved_bundle is not None:
        ctx.obj.bundle_root = resolved_bundle

        # Point the results database at the bundle's results/ directory
        from tribench.storage.connection import set_db_url
        results_dir = ctx.obj.bundle_root / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        set_db_url(f"sqlite:///{results_dir / 'tribench.db'}")

    if verbose:
        click.echo(f"TriBench v{__version__}", err=True)
        if resolved_bundle:
            click.echo(f"Bundle: {resolved_bundle}", err=True)


@cli.command()
def version():
    """Show detailed version information."""
    click.echo(f"TriBench version {__version__}")
    click.echo("A PEEL-inspired benchmarking framework for Trino")
    click.echo(f"Python: {sys.version.split()[0]}")
    click.echo(f"Platform: {sys.platform}")


if __name__ == "__main__":
    cli()