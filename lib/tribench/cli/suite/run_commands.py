"""Suite execution command."""

import click
import sys
import logging
from pathlib import Path

from tribench.cli.base import dry_run_option, verbose_option, config_option, kind_option, ensure_k8s_port_forwarding, auto_ensure_trino_connection
from tribench.core.experiment_suite import ExperimentSuite
from tribench.core.experiment_registry import ExperimentRegistry
from tribench.systems.kubernetes_system import KubernetesSystem
from tribench.utils.config import ConfigurationLoader
from .utils import setup_kubernetes_systems, setup_docker_systems, cleanup_systems, print_suite_summary

logger = logging.getLogger(__name__)


@click.command(name="run")
@click.argument("suite", type=click.Path(exists=True))
@click.option('--exp', '--experiment', 'experiment_filter',
              help='Run only experiments matching this name pattern.')
@click.option('--runs', type=int, help='Override number of runs for all experiments.')
@click.option('--timeout', type=int, help='Override timeout for all experiments.')
@kind_option
@config_option
@dry_run_option
@verbose_option
@click.pass_context
def run_suite(ctx, suite, experiment_filter, runs, timeout, kind, config, dry_run, verbose):
    """Execute all experiments in a suite.
    
    For Kubernetes deployments, use --kind to ensure port forwarding is active.
    
    \b
    Examples:
        tribench suite run experiments/suites/tpch-suite.yaml
        tribench suite run experiments/suites/tpch-suite.yaml --exp tpch-q1
        tribench suite run experiments/suites/tpch-suite.yaml --runs 5 --dry-run
        tribench suite run experiments/suites/tpch-suite.yaml --kind  # For Kubernetes
    """
    ctx.obj.dry_run = dry_run or ctx.obj.dry_run
    ctx.obj.verbose = verbose or ctx.obj.verbose
    
    # Handle Kubernetes port forwarding
    if kind:
        if not ensure_k8s_port_forwarding():
            return
    else:
        # Auto-detect and ensure Trino connection
        auto_ensure_trino_connection()
    
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
        # Handle Kubernetes mode (--kind) with K8s-aware lifecycle management
        systems_to_manage = []
        started_systems = []
        already_running_systems = []
        
        if kind:
            click.echo(f"\n{'='*60}")
            click.echo("Phase 1: Kubernetes System Lifecycle Management")
            click.echo(f"{'='*60}\n")
            
            # Load config for KubernetesSystem
            config_loader = ConfigurationLoader()
            cfg = config_loader.load(experiment_config=config) if config else config_loader.load()
            
            # Create KubernetesSystem instance
            k8s_system = KubernetesSystem(name="kubernetes", config={"config_tree": cfg})
            systems_to_manage = [k8s_system]
            
            # Set up K8s systems
            started_systems, already_running_systems = setup_kubernetes_systems(k8s_system, ctx)
            
        else:
            # Set up Docker systems
            systems_to_manage, started_systems, already_running_systems = setup_docker_systems(
                experiments_to_run, config, ctx
            )
        
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
            cleanup_systems(systems_to_manage, started_systems, already_running_systems, kind, ctx)
        
        # Print summary
        print_suite_summary(exp_suite, results_summary)
        
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
