"""
Bundle management CLI commands.

    tribench bundle create <name>   – scaffold a new bundle
    tribench bundle info            – show bundle metadata
    tribench bundle validate        – check bundle structure
    tribench bundle list            – list experiments in the bundle
    tribench bundle archive         – archive results/ to a tar.gz
"""

import sys
from pathlib import Path
import click

from tribench.cli.base import cli
from tribench.bundle.manifest import (
    Bundle, BundleError, find_bundle_root,
    get_active_bundle, set_active_bundle, clear_active_bundle,
)


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

@cli.group(name="bundle")
def bundle_group():
    """Bundle management commands.

    A bundle is a self-contained directory with everything needed to run
    and reproduce a set of benchmark experiments.

    \b
    Bundle layout:
        my-bundle/
        ├── bundle.yaml       ← manifest (name, version, path overrides)
        ├── queries/          ← workload query directories (apps)
        ├── config/
        │   ├── application.conf
        │   └── hosts/        ← machine-specific .conf files
        ├── datasets/
        ├── experiments/      ← experiment YAML definitions
        ├── log/
        └── results/
    """
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_bundle(bundle_dir: str | None) -> Bundle:
    """
    Resolve the active bundle, erroring out if none is found.

    Priority:
    1. --bundle option passed to the top-level command
    2. Auto-detected from the current working directory (walks up for bundle.yaml)

    Args:
        bundle_dir: Optional explicit path from CLI option.
    """
    if bundle_dir:
        root = Path(bundle_dir)
    else:
        root = find_bundle_root()

    if root is None:
        click.secho(
            "✗ No bundle found. Either run this command from inside a bundle "
            "directory, or pass --bundle <path> to the top-level command.",
            fg='red',
        )
        raise SystemExit(1)

    try:
        return Bundle.load(root)
    except BundleError as exc:
        click.secho(f"✗ {exc}", fg='red')
        raise SystemExit(1)


def _get_bundle_dir(ctx: click.Context) -> str | None:
    """Walk up the Click context stack to find the --bundle option."""
    parent = ctx.parent
    while parent is not None:
        if hasattr(parent, 'params') and 'bundle' in parent.params:
            return parent.params['bundle']
        parent = parent.parent
    return None


# ---------------------------------------------------------------------------
# tribench bundle show / set / clear
# ---------------------------------------------------------------------------

@bundle_group.command(name="show")
def bundle_show():
    """Show the currently active bundle.

    \b
    Examples:
        tribench bundle show
    """
    active = get_active_bundle()
    if active:
        exists_marker = "" if active.exists() else " (directory not found)"
        click.secho(f"Active bundle: {active}{exists_marker}", fg='green' if active.exists() else 'yellow')
    else:
        click.echo("No active bundle set.")
        click.echo("Use 'tribench bundle set <path>' to set one.")


@bundle_group.command(name="set")
@click.argument('bundle_path')
def bundle_set(bundle_path: str):
    """Set a bundle as active (persists across sessions).

    Once set, TriBench uses this bundle automatically without needing
    the --bundle flag on every command.

    \b
    Examples:
        tribench bundle set bundles/tpch
        tribench bundle set /data/bundles/tpcds
    """
    root = Path(bundle_path).resolve()
    if not root.exists():
        click.secho(f"✗ Directory not found: {root}", fg='red', err=True)
        raise SystemExit(1)
    if not (root / Bundle.MANIFEST_FILENAME).exists():
        click.secho(
            f"✗ No bundle.yaml found in {root}. "
            "Is this a valid bundle directory?",
            fg='red', err=True,
        )
        raise SystemExit(1)

    set_active_bundle(root)
    bundle = Bundle.load(root)
    click.secho(f"✓ Active bundle set to '{bundle.name}' ({root})", fg='green')
    click.echo("  Run 'tribench bundle clear' to unset.")


@bundle_group.command(name="clear")
def bundle_clear():
    """Clear the active bundle (revert to --bundle flag / auto-detect).

    \b
    Examples:
        tribench bundle clear
    """
    active = get_active_bundle()
    if active:
        clear_active_bundle()
        click.secho("✓ Active bundle cleared", fg='green')
        click.echo("  TriBench will now require --bundle or auto-detect from CWD.")
    else:
        click.echo("No active bundle was set.")


# ---------------------------------------------------------------------------
# tribench bundle create
# ---------------------------------------------------------------------------

@bundle_group.command(name="create")
@click.argument("name")
@click.option("--path", "bundle_path", default=None,
              help="Directory to create the bundle in. Defaults to bundles/<name>.")
@click.option("--version", default="1.0.0", show_default=True,
              help="Bundle version string.")
@click.option("--description", default="", help="Short description of the bundle.")
def bundle_create(name: str, bundle_path: str | None, version: str, description: str):
    """Scaffold a new bundle directory.

    Bundles are created inside the bundles/ folder by default.

    \b
    Examples:
        tribench bundle create my-benchmark
        tribench bundle create tpch-iceberg --description "TPC-H on Iceberg/Trino"
        tribench bundle create tpcds --path /data/custom/tpcds
    """
    if bundle_path:
        root = Path(bundle_path)
    else:
        # Default: bundles/<name> relative to CWD (or bundle root if inside one)
        bundles_dir = find_bundle_root()
        base = (bundles_dir if bundles_dir else Path.cwd())
        root = base / "bundles" / name

    if root.exists() and (root / "bundle.yaml").exists():
        click.secho(f"✗ A bundle already exists at {root}", fg='red')
        sys.exit(1)

    try:
        bundle = Bundle.create(root, name=name, version=version, description=description)
        click.secho(f"✓ Bundle '{name}' created at {bundle.root}", fg='green')
        click.echo()
        click.echo("Bundle structure:")
        for subdir in sorted(bundle.root.iterdir()):
            if subdir.is_dir():
                click.echo(f"  {subdir.name}/")
            else:
                click.echo(f"  {subdir.name}")
        click.echo()
        click.echo("Templates included as starting points:")
        click.echo(f"  config/hosts/example.conf              ← host profile template")
        click.echo(f"  experiments/experiment-template.yaml   ← single experiment template")
        click.echo(f"  experiments/suites/suite-template.yaml ← suite template")
        click.echo()
        click.echo("Next steps:")
        click.echo(f"  cd {bundle.root}")
        click.echo("  # 1. Copy & edit config/hosts/example.conf → config/hosts/<profile>.conf")
        click.echo("  #    then: tribench config profile set <profile>")
        click.echo("  # 2. Add experiment YAMLs to experiments/  (use experiment-template.yaml)")
        click.echo("  # 3. Add query files to queries/")
        click.echo("  tribench bundle validate")
    except BundleError as exc:
        click.secho(f"✗ {exc}", fg='red')
        sys.exit(1)


# ---------------------------------------------------------------------------
# tribench bundle info
# ---------------------------------------------------------------------------

@bundle_group.command(name="info")
@click.pass_context
def bundle_info(ctx: click.Context):
    """Show bundle metadata and resolved paths.

    \b
    Examples:
        tribench bundle info
        tribench --bundle /data/bundles/tpch bundle info
    """
    bundle = _require_bundle(_get_bundle_dir(ctx))
    click.echo(bundle.summary())


# ---------------------------------------------------------------------------
# tribench bundle validate
# ---------------------------------------------------------------------------

@bundle_group.command(name="validate")
@click.pass_context
def bundle_validate(ctx: click.Context):
    """Check that the bundle has all required directories and files.

    \b
    Examples:
        tribench bundle validate
        tribench --bundle /data/bundles/tpch bundle validate
    """
    bundle = _require_bundle(_get_bundle_dir(ctx))
    click.echo(f"Validating bundle '{bundle.name}' at {bundle.root} …")
    issues = bundle.validate()

    if issues:
        click.secho(f"✗ {len(issues)} issue(s) found:", fg='red')
        for issue in issues:
            click.secho(f"  • {issue}", fg='yellow')
        sys.exit(1)
    else:
        click.secho("✓ Bundle is valid", fg='green')


# ---------------------------------------------------------------------------
# tribench bundle list
# ---------------------------------------------------------------------------

@bundle_group.command(name="list")
@click.pass_context
def bundle_list(ctx: click.Context):
    """List all experiment YAML files in the bundle.

    \b
    Examples:
        tribench bundle list
        tribench --bundle /data/bundles/tpch bundle list
    """
    bundle = _require_bundle(_get_bundle_dir(ctx))
    experiments = bundle.list_experiments()

    if not experiments:
        click.echo(f"No experiments found in {bundle.experiments_path}")
        return

    click.echo(f"Experiments in bundle '{bundle.name}':")
    for exp in experiments:
        rel = exp.relative_to(bundle.root)
        click.echo(f"  {rel}")

    click.echo(f"\nTotal: {len(experiments)} experiment(s)")


# ---------------------------------------------------------------------------
# tribench bundle archive
# ---------------------------------------------------------------------------

@bundle_group.command(name="archive")
@click.option("--output", "output_dir", default=None,
              help="Directory to write the archive to. Defaults to the bundle root.")
@click.pass_context
def bundle_archive(ctx: click.Context, output_dir: str | None):
    """Archive the bundle's results/ directory to a compressed .tar.gz file.

    \b
    Examples:
        tribench bundle archive
        tribench bundle archive --output ~/backups
        tribench --bundle /data/bundles/tpch bundle archive
    """
    bundle = _require_bundle(_get_bundle_dir(ctx))
    out = Path(output_dir) if output_dir else None

    try:
        archive_path = bundle.archive(output_dir=out)
        click.secho(f"✓ Results archived to: {archive_path}", fg='green')
    except BundleError as exc:
        click.secho(f"✗ {exc}", fg='red')
        sys.exit(1)
