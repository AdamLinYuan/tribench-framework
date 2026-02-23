"""Shared utilities for data commands."""

from pathlib import Path
from typing import List, Optional
from tribench.utils.config import ConfigurationLoader
from tribench.bundle.manifest import find_bundle_root, Bundle


def get_datasets_root(config=None, bundle_root: Optional[Path] = None) -> Path:
    """Return the primary datasets root directory.

    Priority:
    1. Active bundle's datasets/ directory  (if a bundle is active)
    2. Framework-level datasets/ directory  (fallback)

    Args:
        config:      Optional config file path.
        bundle_root: Explicit bundle root path (from --bundle flag / ctx.obj).
    """
    loader = ConfigurationLoader(bundle_root=bundle_root)

    # If a bundle is active and has a datasets directory, prefer it
    if loader.active_bundle:
        bundle_datasets = loader.active_bundle.datasets_path
        if bundle_datasets.exists():
            return bundle_datasets

    # Fall back to framework-level datasets/
    full_config = loader.load(experiment_config=config)
    return Path(full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets"))


def get_all_datasets_roots(config=None, bundle_root: Optional[Path] = None) -> List[Path]:
    """Return all dataset search paths in priority order.

    Used for searching datasets across bundle and framework locations.

    Returns:
        List of Paths to search, highest priority first:
        [bundle datasets/, framework datasets/]
    """
    loader = ConfigurationLoader(bundle_root=bundle_root)
    roots: List[Path] = []

    if loader.active_bundle:
        roots.append(loader.active_bundle.datasets_path)

    # Always include the framework-level path too
    full_config = loader.load(experiment_config=config)
    framework_datasets = Path(
        full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets")
    )
    if framework_datasets not in roots:
        roots.append(framework_datasets)

    return roots


def get_trino_connection_params(config=None, bundle_root: Optional[Path] = None):
    """Get Trino connection parameters from configuration.
    
    Args:
        config:      Optional configuration file path.
        bundle_root: Explicit bundle root path.
        
    Returns:
        ConnectionConfig: Trino connection parameters
    """
    from tribench.config import ConnectionConfig
    from tribench.defaults import Defaults

    config_loader = ConfigurationLoader(bundle_root=bundle_root)
    full_config = config_loader.load(experiment_config=config)
    
    trino_config = full_config.get("tribench", {}).get("systems", {}).get("trino", {})
    coordinator_config = trino_config.get("coordinator", {})
    
    connection_params = ConnectionConfig.from_dict({
        'host': coordinator_config.get('host', Defaults.Trino.HOST),
        'port': coordinator_config.get('port', Defaults.Trino.PORT),
        'user': Defaults.Trino.USER
    })
    
    return connection_params
