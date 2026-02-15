"""Shared utilities for suite commands."""

import sys
import click
import logging

logger = logging.getLogger(__name__)


def setup_kubernetes_systems(k8s_system, ctx):
    """Set up Kubernetes systems for suite execution.
    
    Args:
        k8s_system: KubernetesSystem instance
        ctx: Click context
        
    Returns:
        tuple: (started_systems, already_running_systems)
    """
    started_systems = []
    already_running_systems = []
    k8s_was_running = False
    
    try:
        # Check K8s system status
        click.echo("Checking Kubernetes system status...")
        status_info = k8s_system.status()
        
        # Check component status
        pods = status_info.get('pods', [])
        trino_ready = any(p.get('name', '').startswith('trino') and p.get('ready') for p in pods)
        minio_ready = any(p.get('name', '').startswith('minio') and p.get('ready') for p in pods)
        hive_ready = any(p.get('name', '').startswith('hive') and p.get('ready') for p in pods)
        postgres_ready = any(p.get('name', '').startswith('postgresql') and p.get('ready') for p in pods)
        
        # Display status
        for pod in pods:
            status_icon = "✓" if pod.get('ready') else "○"
            status_color = "green" if pod.get('ready') else "yellow"
            click.secho(f"  {status_icon} {pod['name']}: {pod['status']}", fg=status_color)
        
        all_ready = trino_ready and minio_ready and hive_ready and postgres_ready
        
        if all_ready:
            click.secho("\n✓ All Kubernetes systems are running and healthy", fg='green')
            k8s_was_running = True
            already_running_systems.append(k8s_system)
        else:
            # Start missing components
            click.secho("\n⚠ Some systems are not ready, starting...", fg='yellow')
            
            if not minio_ready:
                click.echo("  Starting MinIO...")
                k8s_system.start(component="minio")
                click.secho("  ✓ MinIO started", fg='green')
            
            if not postgres_ready or not hive_ready:
                click.echo("  Starting PostgreSQL and Hive Metastore...")
                k8s_system.start(component="hive-metastore")
                click.secho("  ✓ PostgreSQL and Hive Metastore started", fg='green')
            
            if not trino_ready:
                click.echo("  Starting Trino...")
                k8s_system.start(component="trino")
                click.secho("  ✓ Trino started", fg='green')
            
            started_systems.append(k8s_system)
            click.secho("\n✓ All Kubernetes systems started successfully", fg='green')
        
        # Ensure port forwarding is active
        click.echo("\nEnsuring port forwarding...")
        if not k8s_system.is_port_forwarding_active():
            k8s_system.start_port_forwarding()
            click.secho("✓ Port forwarding started", fg='green')
        else:
            click.secho("✓ Port forwarding already active", fg='green')
            
    except Exception as e:
        click.secho(f"\n✗ Failed to start Kubernetes systems: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)
    
    return started_systems, already_running_systems


def setup_docker_systems(experiments_to_run, config, ctx):
    """Set up Docker systems for suite execution.
    
    Args:
        experiments_to_run: List of experiments to run
        config: Configuration file path
        ctx: Click context
        
    Returns:
        tuple: (systems_to_manage, started_systems, already_running_systems)
    """
    from tribench.utils.config import ConfigurationLoader
    from tribench.systems.trino import TrinoSystem
    from tribench.systems.postgresql import PostgreSQLSystem
    from tribench.systems.minio import MinIOSystem
    from tribench.systems.hive_metastore import HiveMetastoreSystem
    
    # Identify required systems from experiments and load configuration
    config_loader = ConfigurationLoader()
    cfg = config_loader.load(experiment_config=config) if config else config_loader.load()
    
    # Map system names to instances
    system_map = {}
    required_system_names = set()
    
    # Detect required systems from experiments
    for exp in experiments_to_run:
        required_system_names.add(exp.system)
        
        # Check if experiment uses Iceberg catalog - requires full lakehouse stack
        catalog = None
        if hasattr(exp, 'connection') and isinstance(exp.connection, dict):
            catalog = exp.connection.get('catalog')
        elif hasattr(exp, 'connection') and hasattr(exp.connection, 'catalog'):
            catalog = exp.connection.catalog
        
        if catalog == 'iceberg':
            # Iceberg catalog requires the full lakehouse stack
            logger.debug(f"Experiment {exp.name} uses Iceberg catalog, adding lakehouse dependencies")
            required_system_names.update(['trino', 'hive-metastore', 'minio', 'postgresql'])
    
    # Define dependency order for system startup
    # Systems should start in this order to respect dependencies
    system_startup_order = ['postgresql', 'minio', 'hive-metastore', 'trino']
    
    # Create system instances for required systems in dependency order
    systems_to_manage = []
    for system_name in system_startup_order:
        if system_name not in required_system_names:
            continue  # Skip systems not needed
        
        try:
            if system_name == 'trino':
                system = TrinoSystem(config=cfg)
            elif system_name == 'postgresql':
                system = PostgreSQLSystem(config=cfg)
            elif system_name == 'minio':
                system = MinIOSystem(config=cfg)
            elif system_name == 'hive-metastore':
                system = HiveMetastoreSystem(config=cfg)
            else:
                click.secho(f"✗ Unknown system: {system_name}", fg='red')
                sys.exit(1)
            
            systems_to_manage.append(system)
            logger.debug(f"Will manage system: {system_name}")
        except Exception as e:
            click.secho(f"✗ Failed to load system '{system_name}': {e}", fg='red')
            if ctx.obj.verbose:
                import traceback
                click.echo(traceback.format_exc())
            sys.exit(1)
    
    # Show systems that will be managed
    started_systems = []
    already_running_systems = []
    
    if systems_to_manage:
        click.echo(f"\nSystems required: {', '.join(s.name for s in systems_to_manage)}")
        click.echo(f"{'='*60}")
        click.echo("Phase 1: Checking and starting systems...")
        click.echo(f"{'='*60}\n")
        
        for system in systems_to_manage:
            try:
                # Check current status first
                click.echo(f"Checking {system.name} status...")
                status_info = system.status()
                
                if status_info.get('running') and status_info.get('healthy'):
                    # System is already running and healthy - reuse it!
                    click.secho(f"✓ {system.name} is already running and healthy", fg='green')
                    already_running_systems.append(system)
                    
                elif status_info.get('running') and not status_info.get('healthy'):
                    # System is running but unhealthy - restart it
                    click.secho(f"⚠ {system.name} is running but unhealthy, restarting...", fg='yellow')
                    system.stop()
                    system.start()
                    click.secho(f"✓ {system.name} restarted successfully", fg='green')
                    started_systems.append(system)
                    
                else:
                    # System is not running - setup and start
                    click.echo(f"Setting up {system.name}...")
                    system.setup()
                    click.echo(f"Starting {system.name}...")
                    system.start()
                    started_systems.append(system)
                    click.secho(f"✓ {system.name} is running", fg='green')
                    
            except Exception as e:
                click.secho(f"✗ Failed to start {system.name}: {e}", fg='red')
                if ctx.obj.verbose:
                    import traceback
                    click.echo(traceback.format_exc())
                
                # Cleanup only systems we started (not ones that were already running)
                if started_systems:
                    click.echo("\nCleaning up systems we started...")
                    for started_sys in reversed(started_systems):
                        try:
                            click.echo(f"Stopping {started_sys.name}...")
                            started_sys.stop()
                        except Exception as cleanup_err:
                            logger.error(f"Cleanup error for {started_sys.name}: {cleanup_err}")
                
                sys.exit(1)
    
    return systems_to_manage, started_systems, already_running_systems


def cleanup_systems(systems_to_manage, started_systems, already_running_systems, config, ctx):
    """Clean up systems after suite execution.
    
    Args:
        systems_to_manage: All systems that were managed
        started_systems: Systems that were started by this suite
        already_running_systems: Systems that were already running
        config: Configuration tree to determine backend
        ctx: Click context
    """
    from tribench.cli.base import should_use_kubernetes
    
    # Determine if we're in Kubernetes mode
    use_k8s = should_use_kubernetes(config)
    
    if systems_to_manage:
        click.echo(f"\n{'='*60}")
        click.echo("Phase 3: Cleaning up systems...")
        click.echo(f"{'='*60}\n")
        
        # Only stop systems we started (not ones that were already running)
        if started_systems:
            if use_k8s:
                # For K8s, we keep systems running (they take long to restart)
                # But offer user choice
                click.echo("Kubernetes systems were started for this suite.")
                if click.confirm("Keep systems running? (Recommended for faster subsequent runs)", default=True):
                    click.secho("✓ Kubernetes systems left running", fg='green')
                    click.echo("  Use 'tribench sys stop' to stop them manually")
                else:
                    click.echo("Stopping Kubernetes systems...")
                    for system in reversed(started_systems):
                        try:
                            click.echo(f"Stopping {system.name}...")
                            system.stop()
                            click.secho(f"✓ {system.name} stopped", fg='green')
                        except Exception as e:
                            click.secho(f"✗ Stop error for {system.name}: {e}", fg='yellow')
            else:
                # Local Docker systems - stop as normal
                click.echo("Stopping systems we started...")
                for system in reversed(started_systems):
                    try:
                        click.echo(f"Stopping {system.name}...")
                        system.stop()
                        click.secho(f"✓ {system.name} stopped", fg='green')
                    except Exception as e:
                        click.secho(f"✗ Stop error for {system.name}: {e}", fg='yellow')
                        if ctx.obj.verbose:
                            import traceback
                            click.echo(traceback.format_exc())
                        # Continue cleanup of other systems
        
        # Note about already-running systems
        if already_running_systems:
            click.echo(f"\nSystems left running (were already running):")
            for system in already_running_systems:
                click.secho(f"  • {system.name}", fg='cyan')


def print_suite_summary(exp_suite, results_summary):
    """Print suite execution summary.
    
    Args:
        exp_suite: ExperimentSuite instance
        results_summary: List of result dictionaries
    """
    click.echo(f"\n{'='*60}")
    click.echo("Suite Execution Summary")
    click.echo(f"{'='*60}")
    click.echo(f"Suite: {exp_suite.name}")
    click.echo(f"Total experiments: {len(results_summary)}")
    
    passed = sum(1 for r in results_summary if r['status'] == 'PASS')
    failed = sum(1 for r in results_summary if r['status'] == 'FAIL')
    errors = sum(1 for r in results_summary if r['status'] == 'ERROR')
    
    click.echo(f"\nResults:")
    click.secho(f"  Passed:  {passed}", fg='green')
    if failed > 0:
        click.secho(f"  Failed:  {failed}", fg='yellow')
    if errors > 0:
        click.secho(f"  Errors:  {errors}", fg='red')
    
    click.echo(f"\nDetails:")
    for result in results_summary:
        if result['status'] == 'PASS':
            click.secho(f"  ✓ {result['name']}", fg='green')
        elif result['status'] == 'FAIL':
            click.secho(f"  ✗ {result['name']} (validation failed)", fg='yellow')
        else:
            click.secho(f"  ✗ {result['name']} ({result.get('error', 'unknown error')})", fg='red')
    
    click.echo(f"\nResults saved to: results/")
    
    if errors > 0:
        click.secho(f"\n⚠ Suite completed with errors", fg='red')
        sys.exit(1)
    elif failed > 0:
        click.secho(f"\n⚠ Suite completed with validation failures", fg='yellow')
    else:
        click.secho(f"\n✓ Suite completed successfully", fg='green')
