"""Unit tests for CLI commands."""

import pytest
from click.testing import CliRunner
from tribench.cli.base import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.mark.unit
class TestCLI:
    """Tests for base CLI."""
    
    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'TriBench' in result.output
        assert 'Trino Benchmarking Framework' in result.output
    
    def test_cli_version(self, runner):
        """Test version command."""
        result = runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert 'TriBench version' in result.output


@pytest.mark.unit
class TestSystemCommands:
    """Tests for system commands."""
    
    def test_sys_help(self, runner):
        """Test sys command help."""
        result = runner.invoke(cli, ['sys', '--help'])
        assert result.exit_code == 0
        assert 'System lifecycle' in result.output
    
    def test_sys_setup_dry_run(self, runner):
        """Test sys setup with dry-run."""
        result = runner.invoke(cli, ['sys', 'setup', 'trino', '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY RUN' in result.output
    
    def test_sys_status(self, runner):
        """Test sys status command."""
        result = runner.invoke(cli, ['sys', 'status'])
        assert result.exit_code == 0


@pytest.mark.unit
class TestExperimentCommands:
    """Tests for experiment commands."""
    
    def test_exp_help(self, runner):
        """Test exp command help."""
        result = runner.invoke(cli, ['exp', '--help'])
        assert result.exit_code == 0
        assert 'Experiment execution' in result.output
    
    def test_exp_list(self, runner):
        """Test exp list command."""
        result = runner.invoke(cli, ['exp', 'list'])
        assert result.exit_code == 0


@pytest.mark.unit
class TestDataCommands:
    """Tests for data commands."""
    
    def test_data_help(self, runner):
        """Test data command help."""
        result = runner.invoke(cli, ['data', '--help'])
        assert result.exit_code == 0
        assert 'Dataset management' in result.output
    
    def test_data_generate_dry_run(self, runner):
        """Test data generate with dry-run."""
        result = runner.invoke(cli, ['data', 'generate', 'tpch-sf1', '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY RUN' in result.output
    
    def test_data_list(self, runner):
        """Test data list command."""
        result = runner.invoke(cli, ['data', 'list'])
        assert result.exit_code == 0


@pytest.mark.unit
class TestResultCommands:
    """Tests for result commands."""
    
    def test_res_help(self, runner):
        """Test res command help."""
        result = runner.invoke(cli, ['res', '--help'])
        assert result.exit_code == 0
        assert 'Result viewing' in result.output
    
    def test_res_list(self, runner):
        """Test res list command."""
        result = runner.invoke(cli, ['res', 'list'])
        assert result.exit_code == 0
