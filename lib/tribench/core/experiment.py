"""Experiment abstraction for benchmark experiments."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""

    name: str
    description: str
    system: str  # e.g., "trino", "postgresql"
    dataset: Optional[str] = None  # Dataset name (optional for custom queries)
    queries: List[str] = field(default_factory=list)  # List of SQL queries or paths
    query_files: List[str] = field(default_factory=list)  # Paths to query files
    
    # Execution parameters
    runs: int = 1  # Number of times to execute
    warmup_runs: int = 0  # Number of warmup runs (not measured)
    timeout_seconds: int = 300  # Query timeout
    max_retries: int = 3  # Maximum retry attempts on failure
    
    # Connection parameters
    connection: Dict[str, Any] = field(default_factory=dict)  # System connection config
    
    # Validation rules
    validation: Dict[str, Any] = field(default_factory=dict)  # Result validation rules
    
    # Metrics to collect
    metrics: List[str] = field(default_factory=lambda: ["execution_time", "rows_returned"])
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        Deep merge override dict into base dict (modifies base in-place).
        
        Args:
            base: Base dictionary to merge into
            override: Override dictionary with values to merge
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                ExperimentConfig._deep_merge(base[key], value)
            else:
                # Override value
                base[key] = value
    
    @classmethod
    def from_yaml(cls, yaml_path: Path, cli_overrides: Optional[Dict[str, Any]] = None, 
                  suite_config: Optional[Dict[str, Any]] = None) -> "ExperimentConfig":
        """
        Load experiment configuration from YAML file.
        
        Args:
            yaml_path: Path to YAML configuration file
            cli_overrides: Optional CLI parameter overrides
            suite_config: Optional suite-level defaults to merge
            
        Returns:
            ExperimentConfig instance
            
        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML is invalid or missing required fields
        """
        yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Experiment config not found: {yaml_path}")
        
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise ValueError("Empty YAML configuration")
            
            # Validate required fields
            required_fields = ["name", "system"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Helper to normalize value to list
            def normalize_to_list(value):
                if value is None:
                    return []
                if isinstance(value, str):
                    return [value]
                if isinstance(value, list):
                    return value
                return []
            
            # Set defaults for optional fields
            config_data = {
                "name": data["name"],
                "description": data.get("description", ""),
                "system": data["system"],
                "dataset": data.get("dataset"),
                "queries": data.get("queries", []),
                "query_files": normalize_to_list(data.get("query_files")),
                "runs": data.get("runs", 1),
                "warmup_runs": data.get("warmup_runs", 0),
                "timeout_seconds": data.get("timeout_seconds", 300),
                "max_retries": data.get("max_retries", 3),
                "connection": data.get("connection", {}),
                "validation": data.get("validation", {}),
                "metrics": data.get("metrics", ["execution_time", "rows_returned"]),
                "metadata": data.get("metadata", {}),
            }
            
            # Apply suite defaults first (lowest priority)
            if suite_config:
                for key, value in suite_config.items():
                    # Only apply if not already set in experiment config
                    # Special handling for nested dicts (merge them)
                    if key in ["connection", "validation", "metadata"]:
                        if isinstance(value, dict):
                            # Merge suite defaults with experiment config
                            suite_defaults = value.copy()
                            suite_defaults.update(config_data.get(key, {}))
                            config_data[key] = suite_defaults
                    elif key not in data:  # Only use suite default if not in experiment YAML
                        config_data[key] = value
                        logger.debug(f"Suite default: {key} = {value}")
            
            # Apply CLI overrides if provided (highest priority)
            if cli_overrides:
                for key, value in cli_overrides.items():
                    if key in config_data and value is not None:
                        config_data[key] = value
                        logger.debug(f"CLI override: {key} = {value}")
            
            logger.info(f"Loaded experiment config: {config_data['name']}")
            return cls(**config_data)
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {yaml_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load experiment config: {e}") from e
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "system": self.system,
            "dataset": self.dataset,
            "queries": self.queries,
            "query_files": self.query_files,
            "runs": self.runs,
            "warmup_runs": self.warmup_runs,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "connection": self.connection,
            "validation": self.validation,
            "metrics": self.metrics,
            "metadata": self.metadata,
        }


class Experiment(ABC):
    """
    Abstract base class for benchmark experiments.

    An Experiment represents a single benchmark run with specific
    parameters, workload, and success criteria.
    """

    def __init__(self, config: ExperimentConfig):
        """
        Initialize an Experiment.

        Args:
            config: Experiment configuration
        """
        self.config = config
        self.start_time: datetime = None
        self.end_time: datetime = None
        self.results: Dict[str, Any] = {}
        self.status: str = "pending"  # pending, running, completed, failed

    @abstractmethod
    def prepare(self) -> None:
        """
        Prepare the experiment (validate config, check dependencies).

        Raises:
            ExperimentError: If preparation fails
        """
        pass

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Execute the experiment.

        Returns:
            Dictionary containing experiment results

        Raises:
            ExperimentError: If execution fails
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate experiment results.

        Returns:
            True if validation passes, False otherwise
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up resources after experiment completion.
        """
        pass

    def get_duration(self) -> float:
        """
        Get experiment duration in seconds.

        Returns:
            Duration in seconds, or None if not completed
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
