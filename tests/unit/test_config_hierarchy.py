"""
Unit tests for configuration override hierarchy.

Tests the hierarchical configuration merging:
Global defaults → Suite defaults → Experiment YAML → CLI overrides
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from tribench.core.experiment import ExperimentConfig
from tribench.core.experiment_suite import ExperimentSuite


@pytest.mark.unit
class TestConfigurationHierarchy:
    """Test suite for hierarchical configuration merging."""
    
    def test_basic_experiment_load(self):
        """Test loading experiment with no overrides uses YAML values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_yaml = Path(tmpdir) / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino',
                'runs': 3,
                'timeout_seconds': 600
            }))
            
            config = ExperimentConfig.from_yaml(exp_yaml)
            
            assert config.name == 'test-exp'
            assert config.system == 'trino'
            assert config.runs == 3
            assert config.timeout_seconds == 600
    
    def test_suite_defaults_override_global(self):
        """Test suite defaults override global defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_yaml = Path(tmpdir) / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino'
                # No runs specified - should use suite default
            }))
            
            suite_defaults = {
                'runs': 5,
                'timeout_seconds': 900
            }
            
            config = ExperimentConfig.from_yaml(
                exp_yaml,
                suite_config=suite_defaults
            )
            
            # Suite defaults should be used
            assert config.runs == 5
            assert config.timeout_seconds == 900
    
    def test_experiment_yaml_overrides_suite(self):
        """Test experiment YAML overrides suite defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_yaml = Path(tmpdir) / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino',
                'runs': 10  # Explicitly set in experiment
            }))
            
            suite_defaults = {
                'runs': 5,  # Suite default
                'timeout_seconds': 900
            }
            
            config = ExperimentConfig.from_yaml(
                exp_yaml,
                suite_config=suite_defaults
            )
            
            # Experiment YAML should override suite default for runs
            assert config.runs == 10
            # But still use suite default for timeout
            assert config.timeout_seconds == 900
    
    def test_cli_overrides_everything(self):
        """Test CLI overrides have highest precedence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_yaml = Path(tmpdir) / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino',
                'runs': 10,
                'timeout_seconds': 600
            }))
            
            suite_defaults = {
                'runs': 5,
                'timeout_seconds': 900
            }
            
            cli_overrides = {
                'runs': 20,  # CLI override
                'warmup_runs': 2  # New value from CLI
            }
            
            config = ExperimentConfig.from_yaml(
                exp_yaml,
                suite_config=suite_defaults,
                cli_overrides=cli_overrides
            )
            
            # CLI overrides should win
            assert config.runs == 20
            assert config.warmup_runs == 2
            # Experiment YAML value used for timeout (no CLI override)
            assert config.timeout_seconds == 600
    
    def test_deep_merge_dicts(self):
        """Test deep merge of nested dictionaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_yaml = Path(tmpdir) / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino',
                'validation': {
                    'min_success_rate': 0.99,
                    'check_variance': True
                }
            }))
            
            suite_defaults = {
                'validation': {
                    'min_success_rate': 0.95,
                    'max_variance': 0.1,
                    'check_outliers': True
                }
            }
            
            config = ExperimentConfig.from_yaml(
                exp_yaml,
                suite_config=suite_defaults
            )
            
            # Should deep merge validation dicts
            assert config.validation['min_success_rate'] == 0.99  # From experiment
            assert config.validation['max_variance'] == 0.1  # From suite
            assert config.validation['check_variance'] is True  # From experiment
            assert config.validation['check_outliers'] is True  # From suite
    
    def test_list_override_not_append(self):
        """Test lists are overridden, not appended."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_yaml = Path(tmpdir) / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino',
                'metrics': ['execution_time', 'cpu_time']
            }))
            
            suite_defaults = {
                'metrics': ['execution_time', 'rows_returned', 'memory_peak']
            }
            
            config = ExperimentConfig.from_yaml(
                exp_yaml,
                suite_config=suite_defaults
            )
            
            # Experiment list should completely replace suite list
            assert config.metrics == ['execution_time', 'cpu_time']
            assert 'rows_returned' not in config.metrics
    
    def test_full_hierarchy_precedence(self):
        """Test complete precedence chain: global → suite → exp → CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_yaml = Path(tmpdir) / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino',
                'runs': 10,  # Experiment level
                'timeout_seconds': 600  # Experiment level
                # warmup_runs: not specified, will use suite default
                # max_retries: not specified anywhere, will use global default
            }))
            
            suite_defaults = {
                'runs': 5,  # Will be overridden by experiment
                'warmup_runs': 2,  # Will be used
                'timeout_seconds': 900  # Will be overridden by experiment
            }
            
            cli_overrides = {
                'runs': 20  # Will override everything
            }
            
            config = ExperimentConfig.from_yaml(
                exp_yaml,
                suite_config=suite_defaults,
                cli_overrides=cli_overrides
            )
            
            assert config.runs == 20  # CLI wins
            assert config.warmup_runs == 2  # Suite default
            assert config.timeout_seconds == 600  # Experiment YAML
            assert config.max_retries == 3  # Global default


@pytest.mark.unit
class TestExperimentSuite:
    """Test suite for ExperimentSuite class."""
    
    def test_suite_basic_load(self):
        """Test loading a basic suite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create experiment
            exp_yaml = tmpdir / "exp1.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'exp1',
                'system': 'trino'
            }))
            
            # Create suite
            suite_yaml = tmpdir / "suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'test-suite',
                'description': 'Test suite',
                'experiments': [
                    {'path': 'exp1.yaml'}
                ]
            }))
            
            suite = ExperimentSuite.from_yaml(suite_yaml)
            
            assert suite.name == 'test-suite'
            assert suite.description == 'Test suite'
            assert len(suite.experiments) == 1
            assert suite.experiments[0].name == 'exp1'
    
    def test_suite_with_defaults(self):
        """Test suite applies defaults to experiments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create experiments
            exp1_yaml = tmpdir / "exp1.yaml"
            exp1_yaml.write_text(yaml.dump({
                'name': 'exp1',
                'system': 'trino'
            }))
            
            exp2_yaml = tmpdir / "exp2.yaml"
            exp2_yaml.write_text(yaml.dump({
                'name': 'exp2',
                'system': 'trino',
                'runs': 10  # Override suite default
            }))
            
            # Create suite with defaults
            suite_yaml = tmpdir / "suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'test-suite',
                'defaults': {
                    'runs': 5,
                    'timeout_seconds': 600
                },
                'experiments': [
                    {'path': 'exp1.yaml'},
                    {'path': 'exp2.yaml'}
                ]
            }))
            
            suite = ExperimentSuite.from_yaml(suite_yaml)
            
            # First experiment should use suite defaults
            assert suite.experiments[0].runs == 5
            assert suite.experiments[0].timeout_seconds == 600
            
            # Second experiment overrides runs but uses timeout
            assert suite.experiments[1].runs == 10
            assert suite.experiments[1].timeout_seconds == 600
    
    def test_suite_per_experiment_overrides(self):
        """Test per-experiment overrides in suite YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create experiment
            exp_yaml = tmpdir / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'exp1',
                'system': 'trino'
            }))
            
            # Create suite with per-experiment override
            suite_yaml = tmpdir / "suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'test-suite',
                'defaults': {
                    'runs': 3
                },
                'experiments': [
                    {
                        'path': 'exp.yaml',
                        'runs': 7,  # Per-experiment override
                        'warmup_runs': 2
                    }
                ]
            }))
            
            suite = ExperimentSuite.from_yaml(suite_yaml)
            
            # Should use per-experiment override
            assert suite.experiments[0].runs == 7
            assert suite.experiments[0].warmup_runs == 2
    
    def test_suite_relative_paths(self):
        """Test suite resolves relative experiment paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create subdirectory for experiments
            exp_dir = tmpdir / "experiments"
            exp_dir.mkdir()
            
            exp_yaml = exp_dir / "exp1.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'exp1',
                'system': 'trino'
            }))
            
            # Create suite in parent directory
            suite_yaml = tmpdir / "suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'test-suite',
                'experiments': [
                    {'path': 'experiments/exp1.yaml'}  # Relative path
                ]
            }))
            
            suite = ExperimentSuite.from_yaml(suite_yaml)
            
            assert len(suite.experiments) == 1
            assert suite.experiments[0].name == 'exp1'
    
    def test_suite_utility_methods(self):
        """Test suite utility methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            exp_yaml = tmpdir / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino'
            }))
            
            suite_yaml = tmpdir / "suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'test-suite',
                'experiments': [{'path': 'exp.yaml'}]
            }))
            
            suite = ExperimentSuite.from_yaml(suite_yaml)
            
            # Test list_experiments
            exp_names = suite.list_experiments()
            assert exp_names == ['test-exp']
            
            # Test get_experiment
            exp = suite.get_experiment('test-exp')
            assert exp is not None
            assert exp.name == 'test-exp'
            
            # Test get non-existent experiment
            assert suite.get_experiment('nonexistent') is None
            
            # Test __len__
            assert len(suite) == 1
            
            # Test __repr__
            repr_str = repr(suite)
            assert 'test-suite' in repr_str
            assert 'experiments=1' in repr_str

