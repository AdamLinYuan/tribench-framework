"""Experiment suite execution commands."""

import click
import sys
import logging
from pathlib import Path
from tribench.cli.base import cli, dry_run_option, verbose_option, config_option
from tribench.core.experiment_suite import ExperimentSuite
from tribench.core.experiment_registry import ExperimentRegistry
from tribench.systems.trino import TrinoSystem
from tribench.systems.postgresql import PostgreSQLSystem
from tribench.systems.minio import MinIOSystem
from tribench.systems.hive_metastore import HiveMetastoreSystem
from tribench.utils.config import ConfigurationLoader

logger = logging.getLogger(__name__)


@cli.group(name="suite")
def suite_group():
    """Experiment suite execution commands.
    
    Run and manage collections of experiments with shared configuration.
    """
    pass


@suite_group.command(name="run")
@click.argument("suite", type=click.Path(exists=True))
@click.option('--exp', '--experiment', 'experiment_filter',
              help='Run only experiments matching this name pattern.')
@click.option('--runs', type=int, help='Override number of runs for all experiments.')
@click.option('--timeout', type=int, help='Override timeout for all experiments.')
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def run_suite(ctx, suite, experiment_filter, runs, timeout, config, dry_run, verbose):
    """Execute all experiments in a suite.
    
    \b
    Examples:
        tribench suite run experiments/suites/tpch-suite.yaml
        tribench suite run experiments/suites/tpch-suite.yaml --exp tpch-q1
        tribench suite run experiments/suites/tpch-suite.yaml --runs 5 --dry-run
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Set up logging level
    if ctx.obj.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    suite_path = Path(suite)
    
    try:
        # Load suite
        click.echo(f"Loading suite: {suite_path.name}")
        exp_suite = ExperimentSuite.from_yaml(suite_path)
        
        click.echo(f"\nSuite: {exp_suite.name}")
        if exp_suite.description:
            click.echo(f"Description: {exp_suite.description}")
        
        # Show suite defaults
        if exp_suite.default_config:
            click.echo(f"\nSuite defaults:")
            for key, value in exp_suite.default_config.items():
                if isinstance(value, dict):
                    click.echo(f"  {key}: {{{len(value)} items}}")
                elif isinstance(value, list):
                    click.echo(f"  {key}: [{len(value)} items]")
                else:
                    click.echo(f"  {key}: {value}")
        
        # Filter experiments if requested
        experiments_to_run = exp_suite.experiments
        if experiment_filter:
            experiments_to_run = [
                exp for exp in experiments_to_run
                if experiment_filter.lower() in exp.name.lower()
            ]
            if not experiments_to_run:
                click.secho(f"✗ No experiments match filter: {experiment_filter}", fg='yellow')
                return
            click.echo(f"\nFiltered to {len(experiments_to_run)} experiments matching '{experiment_filter}'")
        
        click.echo(f"\nExperiments to run: {len(experiments_to_run)}")
        for i, exp in enumerate(experiments_to_run, 1):
            click.echo(f"  {i}. {exp.name} ({exp.runs} runs)")
        
        # Build CLI overrides
        cli_overrides = {}
        if runs is not None:
            cli_overrides['runs'] = runs
            click.echo(f"\nCLI override: runs = {runs}")
        if timeout is not None:
            cli_overrides['timeout_seconds'] = timeout
            click.echo(f"CLI override: timeout_seconds = {timeout}")
        
        if ctx.obj.dry_run:
            click.echo(f"\n[DRY RUN] Would execute {len(experiments_to_run)} experiments")
            return
        
        # =====================================================================
        # AUTOMATIC SYSTEM LIFECYCLE MANAGEMENT (PEEL-inspired)
        # =====================================================================
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
        if systems_to_manage:
            click.echo(f"\nSystems required: {', '.join(s.name for s in systems_to_manage)}")
            click.echo(f"{'='*60}")
            click.echo("Phase 1: Checking and starting systems...")
            click.echo(f"{'='*60}\n")
            
            # Track which systems we started vs already running
            started_systems = []
            already_running_systems = []
            
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
        
        # Execute experiments with guaranteed cleanup
        click.echo(f"\n{'='*60}")
        click.echo("Phase 2: Executing experiments...")
        click.echo(f"{'='*60}\n")
        
        results_summary = []
        
        try:
            # Execute each experiment
            for i, exp_config in enumerate(experiments_to_run, 1):
                click.echo(f"\n[{i}/{len(experiments_to_run)}] Executing: {exp_config.name}")
                click.echo("-" * 60)
                
                try:
                    # Apply CLI overrides to this experiment
                    if cli_overrides:
                        from tribench.core.experiment import ExperimentConfig
                        for key, value in cli_overrides.items():
                            setattr(exp_config, key, value)
                    
                    # Create experiment instance
                    experiment = ExperimentRegistry.create(exp_config)
                    
                    # Execute lifecycle
                    experiment.prepare()
                    click.secho("✓ Preparation complete", fg='green')
                    
                    results = experiment.run()
                    click.secho("✓ Execution complete", fg='green')
                    
                    # Validate
                    if experiment.validate():
                        click.secho("✓ Validation passed", fg='green')
                        status = "PASS"
                    else:
                        click.secho("✗ Validation failed", fg='yellow')
                        status = "FAIL"
                    
                    experiment.cleanup()
                    
                    # Track results
                    results_summary.append({
                        'name': exp_config.name,
                        'status': status,
                        'duration': results.get('total_duration_seconds', 0),
                        'runs_completed': results.get('runs_completed', 0)
                    })
                    
                except Exception as e:
                    click.secho(f"✗ Experiment failed: {e}", fg='red')
                    if ctx.obj.verbose:
                        import traceback
                        click.echo(traceback.format_exc())
                    
                    results_summary.append({
                        'name': exp_config.name,
                        'status': 'ERROR',
                        'error': str(e)
                    })
                    
                    # Ask whether to continue
                    if i < len(experiments_to_run):
                        if not click.confirm('\nContinue with remaining experiments?', default=True):
                            break
        
        finally:
            # =====================================================================
            # GUARANTEED CLEANUP - Runs even if experiments fail
            # =====================================================================
            if systems_to_manage:
                click.echo(f"\n{'='*60}")
                click.echo("Phase 3: Cleaning up systems...")
                click.echo(f"{'='*60}\n")
                
                # Only stop systems we started (not ones that were already running)
                if started_systems:
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
        
        # Print summary
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
        
    except FileNotFoundError as e:
        click.secho(f"✗ Error: {e}", fg='red')
        sys.exit(1)
    except ValueError as e:
        click.secho(f"✗ Configuration error: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)


@suite_group.command(name="list")
@click.option('--path', type=click.Path(exists=True), 
              default='experiments/suites',
              help='Directory to search for suites.')
@verbose_option
@click.pass_context
def list_suites(ctx, path, verbose):
    """List available experiment suites.
    
    \b
    Examples:
        tribench suite list
        tribench suite list --path experiments/suites
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    suite_dir = Path(path)
    
    if not suite_dir.exists():
        click.secho(f"✗ Directory not found: {suite_dir}", fg='red')
        return
    
    # Find all YAML files in suite directory
    suite_files = list(suite_dir.glob('*.yaml')) + list(suite_dir.glob('*.yml'))
    
    if not suite_files:
        click.echo(f"No suite files found in {suite_dir}")
        return
    
    click.echo(f"Available suites in {suite_dir}:\n")
    
    for suite_file in sorted(suite_files):
        try:
            suite = ExperimentSuite.from_yaml(suite_file)
            click.echo(f"  {suite.name}")
            if suite.description:
                click.echo(f"    {suite.description}")
            click.echo(f"    Experiments: {len(suite.experiments)}")
            click.echo(f"    File: {suite_file.name}")
            if ctx.obj.verbose and suite.default_config:
                click.echo(f"    Defaults: {list(suite.default_config.keys())}")
            click.echo()
        except Exception as e:
            click.secho(f"  ✗ {suite_file.name}: {e}", fg='yellow')


@suite_group.command(name="show")
@click.argument("suite", type=click.Path(exists=True))
@verbose_option
@click.pass_context
def show_suite(ctx, suite, verbose):
    """Show detailed information about a suite.
    
    \b
    Examples:
        tribench suite show experiments/suites/tpch-suite.yaml
    """
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    suite_path = Path(suite)
    
    try:
        exp_suite = ExperimentSuite.from_yaml(suite_path)
        
        click.echo(f"Suite: {exp_suite.name}")
        click.echo(f"{'='*60}")
        
        if exp_suite.description:
            click.echo(f"\nDescription:")
            click.echo(f"  {exp_suite.description}")
        
        if exp_suite.default_config:
            click.echo(f"\nSuite Defaults:")
            import json
            click.echo(json.dumps(exp_suite.default_config, indent=2))
        
        click.echo(f"\nExperiments ({len(exp_suite.experiments)}):")
        for i, exp in enumerate(exp_suite.experiments, 1):
            click.echo(f"\n  {i}. {exp.name}")
            click.echo(f"     System: {exp.system}")
            click.echo(f"     Runs: {exp.runs}")
            if exp.warmup_runs > 0:
                click.echo(f"     Warmup runs: {exp.warmup_runs}")
            click.echo(f"     Timeout: {exp.timeout_seconds}s")
            if exp.dataset:
                click.echo(f"     Dataset: {exp.dataset}")
            
            query_count = len(exp.queries) + len(exp.query_files)
            click.echo(f"     Queries: {query_count}")
            
            if ctx.obj.verbose:
                if exp.validation:
                    click.echo(f"     Validation: {exp.validation}")
                if exp.metadata:
                    click.echo(f"     Metadata: {exp.metadata}")
        
    except Exception as e:
        click.secho(f"✗ Error: {e}", fg='red')
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)

