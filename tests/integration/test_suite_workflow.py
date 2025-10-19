"""
Integration tests for suite workflow.

Tests the complete workflow:
1. Create suite YAML with defaults
2. Load suite with ExperimentSuite.from_yaml()
3. Verify hierarchical config merging works end-to-end
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from tribench.core.experiment_suite import ExperimentSuite


@pytest.mark.integration
class TestSuiteWorkflow:
    """Integration tests for full suite workflow."""
    
    def test_end_to_end_suite_workflow(self):
        """Test complete workflow from YAML to loaded suite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create multiple experiments
            exp1_yaml = tmpdir / "query1.yaml"
            exp1_yaml.write_text(yaml.dump({
                'name': 'query1',
                'system': 'trino',
                'queries': ['SELECT 1']
            }))
            
            exp2_yaml = tmpdir / "query2.yaml"
            exp2_yaml.write_text(yaml.dump({
                'name': 'query2',
                'system': 'trino',
                'queries': ['SELECT 2'],
                'runs': 15  # Override suite default
            }))
            
            exp3_yaml = tmpdir / "query3.yaml"
            exp3_yaml.write_text(yaml.dump({
                'name': 'query3',
                'system': 'trino',
                'queries': ['SELECT 3'],
                'timeout_seconds': 1200,  # Override suite default
                'validation': {
                    'min_success_rate': 0.99  # Override suite default
                }
            }))
            
            # Create suite with defaults and per-experiment overrides
            suite_yaml = tmpdir / "test-suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'integration-test-suite',
                'description': 'Integration test suite',
                'defaults': {
                    'runs': 5,
                    'warmup_runs': 1,
                    'timeout_seconds': 600,
                    'validation': {
                        'min_success_rate': 0.95,
                        'check_outliers': True
                    }
                },
                'experiments': [
                    {
                        'path': 'query1.yaml'
                        # Uses all suite defaults
                    },
                    {
                        'path': 'query2.yaml',
                        'warmup_runs': 3  # Per-experiment override in suite
                    },
                    {
                        'path': 'query3.yaml'
                        # Has overrides in its own YAML
                    }
                ]
            }))
            
            # Load suite
            suite = ExperimentSuite.from_yaml(suite_yaml)
            
            # Verify suite metadata
            assert suite.name == 'integration-test-suite'
            assert suite.description == 'Integration test suite'
            assert len(suite.experiments) == 3
            
            # Verify experiment 1: uses all suite defaults
            exp1 = suite.experiments[0]
            assert exp1.name == 'query1'
            assert exp1.runs == 5  # From suite
            assert exp1.warmup_runs == 1  # From suite
            assert exp1.timeout_seconds == 600  # From suite
            assert exp1.validation['min_success_rate'] == 0.95  # From suite
            assert exp1.validation['check_outliers'] is True  # From suite
            
            # Verify experiment 2: has per-experiment override in suite YAML
            exp2 = suite.experiments[1]
            assert exp2.name == 'query2'
            assert exp2.runs == 15  # From exp YAML (highest precedence)
            assert exp2.warmup_runs == 3  # From suite's per-exp override
            assert exp2.timeout_seconds == 600  # From suite defaults
            
            # Verify experiment 3: has overrides in experiment YAML
            exp3 = suite.experiments[2]
            assert exp3.name == 'query3'
            assert exp3.runs == 5  # From suite
            assert exp3.timeout_seconds == 1200  # From exp YAML
            assert exp3.validation['min_success_rate'] == 0.99  # From exp YAML
            assert exp3.validation['check_outliers'] is True  # From suite (deep merge)
    
    def test_cli_overrides_in_suite_context(self):
        """Test that CLI overrides work when loading from suite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            exp_yaml = tmpdir / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'test-exp',
                'system': 'trino',
                'runs': 10
            }))
            
            suite_yaml = tmpdir / "suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'test-suite',
                'defaults': {
                    'runs': 5
                },
                'experiments': [
                    {
                        'path': 'exp.yaml',
                        'runs': 7  # Per-experiment override in suite
                    }
                ]
            }))
            
            # Load suite normally
            suite = ExperimentSuite.from_yaml(suite_yaml)
            
            # Precedence should be:
            # exp YAML (10) > per-exp in suite (7) > suite defaults (5)
            assert suite.experiments[0].runs == 10
            
            # In actual CLI usage, cli_overrides would be passed to
            # ExperimentConfig.from_yaml() during suite.run() execution
            # This is tested in the unit tests
    
    def test_complex_nested_config_merge(self):
        """Test complex nested configuration merging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            exp_yaml = tmpdir / "exp.yaml"
            exp_yaml.write_text(yaml.dump({
                'name': 'complex-exp',
                'system': 'trino',
                'validation': {
                    'min_success_rate': 0.99,
                    'metrics': ['accuracy', 'precision']
                },
                'metadata': {
                    'author': 'test',
                    'version': '2.0'
                }
            }))
            
            suite_yaml = tmpdir / "suite.yaml"
            suite_yaml.write_text(yaml.dump({
                'name': 'complex-suite',
                'defaults': {
                    'validation': {
                        'min_success_rate': 0.95,
                        'check_outliers': True,
                        'metrics': ['accuracy']
                    },
                    'metadata': {
                        'suite': 'benchmark',
                        'version': '1.0'
                    }
                },
                'experiments': [
                    {
                        'path': 'exp.yaml',
                        'validation': {
                            'max_variance': 0.1
                        }
                    }
                ]
            }))
            
            suite = ExperimentSuite.from_yaml(suite_yaml)
            exp = suite.experiments[0]
            
            # Validation should be deep merged from all sources
            assert exp.validation['min_success_rate'] == 0.99  # From exp YAML
            assert exp.validation['check_outliers'] is True  # From suite defaults
            assert exp.validation['max_variance'] == 0.1  # From suite per-exp override
            assert exp.validation['metrics'] == ['accuracy', 'precision']  # From exp YAML (lists replace)
            
            # Metadata should also be deep merged
            assert exp.metadata['author'] == 'test'  # From exp YAML
            assert exp.metadata['version'] == '2.0'  # From exp YAML (overrides suite)
            assert exp.metadata['suite'] == 'benchmark'  # From suite defaults
