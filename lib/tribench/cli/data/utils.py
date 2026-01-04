"""Shared utilities for data commands."""

from pathlib import Path
from tribench.utils.config import ConfigurationLoader


def get_datasets_root(config=None):
    """Get datasets root directory from configuration.
    
    Args:
        config: Optional configuration file path
        
    Returns:
        Path: Datasets root directory
    """
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    datasets_root = Path(full_config.get("tribench", {}).get("datasets", {}).get("dir", "datasets"))
    return datasets_root


def get_trino_connection_params(config=None):
    """Get Trino connection parameters from configuration.
    
    Args:
        config: Optional configuration file path
        
    Returns:
        ConnectionConfig: Trino connection parameters
    """
    from tribench.config import ConnectionConfig
    from tribench.defaults import Defaults
    from tribench.utils.config import ConfigurationLoader
    
    config_loader = ConfigurationLoader()
    full_config = config_loader.load(experiment_config=config)
    
    trino_config = full_config.get("tribench", {}).get("systems", {}).get("trino", {})
    coordinator_config = trino_config.get("coordinator", {})
    
    connection_params = ConnectionConfig.from_dict({
        'host': coordinator_config.get('host', Defaults.Trino.HOST),
        'port': coordinator_config.get('port', Defaults.Trino.PORT),
        'user': Defaults.Trino.USER
    })
    
    return connection_params
