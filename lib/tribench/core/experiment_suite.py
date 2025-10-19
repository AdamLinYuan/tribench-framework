"""
Experiment Suite - Collection of related experiments.

Inspired by PEEL's ExperimentSuite pattern for managing groups of
experiments with shared configuration and lifecycle.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml
import logging

from tribench.core.experiment import Experiment, ExperimentConfig

logger = logging.getLogger(__name__)


class ExperimentSuite:
    """
    Collection of related experiments with suite-level configuration.
    
    Inspired by PEEL's ExperimentSuite pattern. Allows defining common
    configuration at suite level that is inherited by all experiments,
    with experiments able to override specific values.
    
    Example YAML:
        ```yaml
        name: tpch-suite
        description: TPC-H benchmark suite
        defaults:
          system: trino
          runs: 3
          timeout_seconds: 300
        experiments:
          - path: experiments/q1.yaml
          - path: experiments/q6.yaml
            runs: 5  # Override suite default
        ```
    """
    
    def __init__(self, 
                 name: str,
                 experiments: Optional[List[ExperimentConfig]] = None,
                 default_config: Optional[Dict[str, Any]] = None,
                 description: str = ""):
        """
        Initialize an ExperimentSuite.
        
        Args:
            name: Suite name
            experiments: List of experiment configurations
            default_config: Suite-level defaults applied to all experiments
            description: Suite description
        """
        self.name = name
        self.description = description
        self.experiments = experiments or []
        self.default_config = default_config or {}
        
        logger.info(f"Initialized suite '{name}' with {len(self.experiments)} experiments")
    
    def add_experiment(self, config: ExperimentConfig) -> None:
        """
        Add an experiment to the suite.
        
        Args:
            config: Experiment configuration
        """
        self.experiments.append(config)
        logger.debug(f"Added experiment '{config.name}' to suite '{self.name}'")
    
    def get_experiment(self, name: str) -> Optional[ExperimentConfig]:
        """
        Get experiment by name.
        
        Args:
            name: Experiment name
            
        Returns:
            ExperimentConfig if found, None otherwise
        """
        for exp in self.experiments:
            if exp.name == name:
                return exp
        return None
    
    def list_experiments(self) -> List[str]:
        """
        List all experiment names in the suite.
        
        Returns:
            List of experiment names
        """
        return [exp.name for exp in self.experiments]
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ExperimentSuite":
        """
        Load suite from YAML file with automatic experiment loading.
        
        The suite YAML defines suite-level defaults and lists experiments.
        Each experiment is loaded from its own YAML file with suite defaults
        merged in.
        
        Args:
            yaml_path: Path to suite YAML file
            
        Returns:
            ExperimentSuite instance
            
        Raises:
            FileNotFoundError: If suite YAML or experiment YAMLs don't exist
            ValueError: If YAML is invalid
            
        Example YAML:
            ```yaml
            name: tpch-scalability-study
            description: Study TPC-H query performance at different scales
            defaults:
              system: trino
              runs: 3
              warmup_runs: 1
              timeout_seconds: 600
              validation:
                min_success_rate: 0.95
            experiments:
              - path: experiments/tpch-q1-sf1.yaml
              - path: experiments/tpch-q1-sf10.yaml
              - path: experiments/tpch-q1-sf100.yaml
                runs: 5  # Override for this experiment
              - path: experiments/tpch-q6-sf1.yaml
                timeout_seconds: 300  # Different timeout
            ```
        """
        yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Suite config not found: {yaml_path}")
        
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise ValueError("Empty suite YAML")
            
            # Validate required fields
            if 'name' not in data:
                raise ValueError("Suite must have 'name' field")
            
            if 'experiments' not in data or not data['experiments']:
                raise ValueError("Suite must have at least one experiment")
            
            # Extract suite-level data
            suite_name = data['name']
            description = data.get('description', '')
            suite_defaults = data.get('defaults', {})
            
            logger.info(f"Loading suite '{suite_name}' from {yaml_path}")
            if suite_defaults:
                logger.info(f"Suite defaults: {list(suite_defaults.keys())}")
            
            # Load experiments
            experiments = []
            suite_dir = yaml_path.parent  # Suite YAML location for resolving relative paths
            
            for exp_spec in data['experiments']:
                if isinstance(exp_spec, str):
                    # Simple case: just a path string
                    exp_path = exp_spec
                    exp_overrides = {}
                elif isinstance(exp_spec, dict) and 'path' in exp_spec:
                    # Complex case: path + per-experiment overrides
                    exp_path = exp_spec['path']
                    exp_overrides = {k: v for k, v in exp_spec.items() if k != 'path'}
                else:
                    raise ValueError(
                        f"Invalid experiment specification: {exp_spec}. "
                        "Must be string path or dict with 'path' key"
                    )
                
                # Resolve experiment path (relative to suite YAML)
                if not Path(exp_path).is_absolute():
                    exp_path = suite_dir / exp_path
                
                # Merge: suite defaults → per-experiment overrides
                experiment_defaults = {**suite_defaults}
                if exp_overrides:
                    ExperimentConfig._deep_merge(experiment_defaults, exp_overrides)
                    logger.debug(f"Per-experiment overrides for {exp_path.name}: {list(exp_overrides.keys())}")
                
                # Load experiment with merged defaults
                exp_config = ExperimentConfig.from_yaml(
                    exp_path,
                    suite_config=experiment_defaults
                )
                experiments.append(exp_config)
            
            logger.info(f"Loaded {len(experiments)} experiments for suite '{suite_name}'")
            
            return cls(
                name=suite_name,
                description=description,
                experiments=experiments,
                default_config=suite_defaults
            )
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {yaml_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load suite: {e}") from e
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert suite to dictionary representation.
        
        Returns:
            Dictionary with suite data
        """
        return {
            "name": self.name,
            "description": self.description,
            "default_config": self.default_config,
            "experiments": [exp.to_dict() for exp in self.experiments]
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ExperimentSuite(name='{self.name}', experiments={len(self.experiments)})"
    
    def __len__(self) -> int:
        """Number of experiments in suite."""
        return len(self.experiments)

