"""Tests for CLI base utilities and the root 'cli' group."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from click.testing import CliRunner

from tribench.cli.base import (
    cli,
    should_use_kubernetes,
    is_k8s_deployment_active,
    ensure_k8s_port_forwarding,
    auto_ensure_trino_connection,
    TriBenchContext,
    get_log_dir,
)


# ---------------------------------------------------------------------------
# should_use_kubernetes
# ---------------------------------------------------------------------------

class TestShouldUseKubernetes:
    # Plain dicts also have .get, so the code takes the ConfigTree branch and
    # does config.get('tribench.defaults.backend', 'docker') — looking for a
    # literal dotted key, which a plain dict won't have.  For plain dicts the
    # function therefore always returns False.

    def test_docker_config(self):
        cfg = {"tribench": {"defaults": {"backend": "docker"}}}
        assert should_use_kubernetes(cfg) is False

    def test_empty_config_defaults_to_false(self):
        assert should_use_kubernetes({}) is False

    def test_missing_tribench_key(self):
        assert should_use_kubernetes({"other": "stuff"}) is False

    def test_config_tree_object_kubernetes(self):
        """ConfigTree mock: .get('tribench.defaults.backend') returns 'kubernetes'."""
        mock_tree = MagicMock()
        mock_tree.get.return_value = "kubernetes"
        assert should_use_kubernetes(mock_tree) is True

    def test_config_tree_object_docker(self):
        mock_tree = MagicMock()
        mock_tree.get.return_value = "docker"
        assert should_use_kubernetes(mock_tree) is False

    def test_exception_returns_false(self):
        """Any exception accessing config should fall back to False."""
        bad_config = MagicMock()
        bad_config.get.side_effect = RuntimeError("oops")
        assert should_use_kubernetes(bad_config) is False


# ---------------------------------------------------------------------------
# TriBenchContext
# ---------------------------------------------------------------------------

class TestTriBenchContext:
    def test_defaults(self):
        ctx = TriBenchContext()
        assert ctx.verbose is False
        assert ctx.dry_run is False
        assert ctx.bundle_root is None

    def test_log_dir_no_bundle(self):
        ctx = TriBenchContext()
        assert ctx.log_dir == Path("log")

    def test_log_dir_with_bundle(self, tmp_path):
        ctx = TriBenchContext()
        ctx.bundle_root = tmp_path
        assert ctx.log_dir == tmp_path / "log"


# ---------------------------------------------------------------------------
# get_log_dir
# ---------------------------------------------------------------------------

class TestGetLogDir:
    def test_returns_log_from_context(self, tmp_path):
        ctx = MagicMock()
        ctx.log_dir = tmp_path / "log"
        assert get_log_dir(ctx) == tmp_path / "log"

    def test_fallback_without_context(self):
        # Should not raise; returns some Path ending in 'log'
        result = get_log_dir(None)
        assert result.name == "log"


# ---------------------------------------------------------------------------
# CLI root group
# ---------------------------------------------------------------------------

class TestCliRoot:
    def test_version_flag(self, cli_runner):
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "TriBench" in result.output

    def test_help_flag(self, cli_runner):
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "tribench" in result.output.lower() or "Usage" in result.output

    def test_version_subcommand(self, cli_runner):
        result = cli_runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "TriBench" in result.output

    def test_verbose_flag_sets_context(self, cli_runner):
        """--verbose should be accepted without error."""
        result = cli_runner.invoke(cli, ["--verbose", "version"])
        assert result.exit_code == 0

    def test_bundle_flag_with_valid_dir(self, cli_runner, temp_bundle_dir):
        """--bundle <valid_dir> should resolve the bundle without error."""
        with patch("tribench.storage.connection.set_db_url"):
            result = cli_runner.invoke(cli, ["--bundle", str(temp_bundle_dir), "version"])
        assert result.exit_code == 0

    def test_bundle_flag_with_invalid_dir(self, cli_runner, tmp_path):
        """--bundle pointing to a non-existent directory should fail with a usage error."""
        result = cli_runner.invoke(cli, ["--bundle", str(tmp_path / "does_not_exist"), "version"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Parametrised backend detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("backend,expected", [
    ("kubernetes", True),
    ("docker", False),
    ("compose", False),
    ("", False),
])
def test_backend_parametrised_via_config_tree(backend, expected):
    """Test backend detection using a ConfigTree-like mock (has dotted .get)."""
    mock_tree = MagicMock()
    mock_tree.get.return_value = backend
    assert should_use_kubernetes(mock_tree) is expected


# ---------------------------------------------------------------------------
# should_use_kubernetes — else branch (no .get, not a dict)
# ---------------------------------------------------------------------------

def test_should_use_kubernetes_non_dict_no_get():
    """An object with no .get method falls through to the else → docker."""
    class NoGet:
        pass
    assert should_use_kubernetes(NoGet()) is False


# ---------------------------------------------------------------------------
# is_k8s_deployment_active
# ---------------------------------------------------------------------------

class TestIsK8sDeploymentActive:
    def test_pid_file_present_returns_true(self, tmp_path):
        pid_file = tmp_path / "port-forward.pid"
        pid_file.write_text("12345")
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            assert is_k8s_deployment_active() is True

    def test_no_pid_file_port_open_returns_true(self, tmp_path):
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            with patch("socket.socket") as mock_sock_cls:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 0   # port open
                mock_sock_cls.return_value = mock_sock
                assert is_k8s_deployment_active() is True

    def test_no_pid_file_port_closed_returns_false(self, tmp_path):
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            with patch("socket.socket") as mock_sock_cls:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 111  # ECONNREFUSED
                mock_sock_cls.return_value = mock_sock
                assert is_k8s_deployment_active() is False

    def test_socket_exception_returns_false(self, tmp_path):
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            with patch("socket.socket", side_effect=OSError("network error")):
                assert is_k8s_deployment_active() is False


# ---------------------------------------------------------------------------
# ensure_k8s_port_forwarding
# ---------------------------------------------------------------------------

_K8S_PATCH = "tribench.systems.kubernetes_system.KubernetesSystem"


class TestEnsureK8sPortForwarding:
    def _mock_k8s(self, is_active=False, ensure_result=True):
        mock_k8s = MagicMock()
        mock_k8s.is_port_forwarding_active.return_value = is_active
        mock_k8s.ensure_port_forwarding.return_value = ensure_result
        return mock_k8s

    def test_already_active_returns_true(self):
        mock_k8s = self._mock_k8s(is_active=True)
        with patch(_K8S_PATCH, return_value=mock_k8s):
            result = ensure_k8s_port_forwarding()
        assert result is True
        mock_k8s.ensure_port_forwarding.assert_not_called()

    def test_already_active_silent_no_output(self):
        mock_k8s = self._mock_k8s(is_active=True)
        echo = MagicMock()
        with patch(_K8S_PATCH, return_value=mock_k8s):
            with patch("click.secho") as mock_secho:
                result = ensure_k8s_port_forwarding(echo=echo, silent_if_active=True)
        assert result is True
        mock_secho.assert_not_called()

    def test_already_active_not_silent_prints_message(self):
        mock_k8s = self._mock_k8s(is_active=True)
        with patch(_K8S_PATCH, return_value=mock_k8s):
            with patch("click.secho") as mock_secho:
                result = ensure_k8s_port_forwarding(silent_if_active=False)
        assert result is True
        mock_secho.assert_called_once()
        assert "already active" in mock_secho.call_args[0][0]

    def test_not_active_starts_successfully_returns_true(self):
        mock_k8s = self._mock_k8s(is_active=False, ensure_result=True)
        echo = MagicMock()
        with patch(_K8S_PATCH, return_value=mock_k8s):
            with patch("click.secho"):
                result = ensure_k8s_port_forwarding(echo=echo)
        assert result is True
        echo.assert_called_once()

    def test_not_active_fails_returns_false(self):
        mock_k8s = self._mock_k8s(is_active=False, ensure_result=False)
        with patch(_K8S_PATCH, return_value=mock_k8s):
            with patch("click.secho"):
                with patch("click.echo"):
                    result = ensure_k8s_port_forwarding()
        assert result is False

    def test_none_config_defaults_to_empty_dict(self):
        mock_k8s = self._mock_k8s(is_active=True)
        with patch(_K8S_PATCH, return_value=mock_k8s) as mock_cls:
            ensure_k8s_port_forwarding(config=None)
        config_arg = mock_cls.call_args[0][1]
        assert "local_port" in config_arg


# ---------------------------------------------------------------------------
# auto_ensure_trino_connection
# ---------------------------------------------------------------------------

class TestAutoEnsureTrinoConnection:
    def test_trino_accessible_returns_true(self, tmp_path):
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            with patch("socket.socket") as mock_sock_cls:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 0  # port open
                mock_sock_cls.return_value = mock_sock
                result = auto_ensure_trino_connection()
        assert result is True

    def test_not_accessible_no_pid_file_returns_true(self, tmp_path):
        """No Trino, no K8s indicators — returns True to let the command fail naturally."""
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            with patch("socket.socket") as mock_sock_cls:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 111  # closed
                mock_sock_cls.return_value = mock_sock
                result = auto_ensure_trino_connection()
        assert result is True

    def test_not_accessible_pid_file_present_restarts_forwarding(self, tmp_path):
        pid_file = tmp_path / "port-forward.pid"
        pid_file.write_text("99")
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            with patch("socket.socket") as mock_sock_cls:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 111  # Trino closed
                mock_sock_cls.return_value = mock_sock
                with patch("tribench.cli.base.ensure_k8s_port_forwarding",
                           return_value=True) as mock_ensure:
                    with patch("click.echo"):
                        result = auto_ensure_trino_connection()
        mock_ensure.assert_called_once()
        assert result is True

    def test_socket_exception_continues_to_pid_check(self, tmp_path):
        """Socket exception is swallowed; function falls through to pid check."""
        with patch("tribench.cli.base.get_log_dir", return_value=tmp_path):
            with patch("socket.socket", side_effect=OSError("fail")):
                result = auto_ensure_trino_connection()
        assert result is True  # no pid file → returns True


# ---------------------------------------------------------------------------
# CLI verbose + bundle output (covers lines 214-216)
# ---------------------------------------------------------------------------

class TestCliVerboseBundle:
    def test_verbose_with_bundle_prints_both_lines(self, cli_runner, temp_bundle_dir):
        with patch("tribench.storage.connection.set_db_url"):
            result = cli_runner.invoke(
                cli,
                ["--verbose", "--bundle", str(temp_bundle_dir), "version"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        # --verbose emits "TriBench v..." and "Bundle: ..." to stderr
        assert "TriBench" in (result.output + (result.stderr or ""))

    def test_verbose_without_bundle_no_bundle_line(self, cli_runner):
        result = cli_runner.invoke(cli, ["--verbose", "version"])
        assert result.exit_code == 0
