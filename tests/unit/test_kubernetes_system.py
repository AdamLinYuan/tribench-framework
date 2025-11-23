"""Unit tests for KubernetesSystem."""

import pytest
from unittest.mock import MagicMock, patch
import subprocess
from tribench.systems.kubernetes_system import KubernetesSystem

@pytest.fixture
def k8s_config():
    return {
        "context": "test-context",
        "namespace": "test-ns",
        "helm_chart": "test/chart",
        "helm_release": "test-release",
        "helm_values": "values.yaml",
        "minio_chart": "minio/chart",
        "minio_release": "minio-release",
        "minio_values": "minio-values.yaml"
    }

@pytest.fixture
def k8s_system(k8s_config):
    return KubernetesSystem("test-k8s", k8s_config)

def test_init(k8s_system):
    assert k8s_system.name == "test-k8s"
    assert k8s_system.context == "test-context"
    assert k8s_system.namespace == "test-ns"
    assert k8s_system.minio_chart == "minio/chart"

@patch("subprocess.run")
def test_kubectl_command(mock_run, k8s_system):
    mock_run.return_value.stdout = "output"
    
    k8s_system._kubectl(["get", "pods"])
    
    mock_run.assert_called_with(
        ["kubectl", "--context", "test-context", "--namespace", "test-ns", "get", "pods"],
        check=True,
        capture_output=True,
        text=True
    )

@patch("subprocess.run")
def test_helm_command(mock_run, k8s_system):
    mock_run.return_value.stdout = "output"
    
    k8s_system._helm(["install"])
    
    mock_run.assert_called_with(
        ["helm", "--kube-context", "test-context", "--namespace", "test-ns", "install"],
        check=True,
        capture_output=True,
        text=True
    )

@patch("subprocess.run")
def test_setup(mock_run, k8s_system):
    # Mock successful cluster info and namespace check
    mock_run.return_value.stdout = "ok"
    
    k8s_system.setup()
    
    # Should check cluster info, namespace, and add repos
    # We expect at least 3 calls: cluster-info, get ns, repo add (trino), repo add (bitnami), repo update
    assert mock_run.call_count >= 3

@patch("subprocess.Popen")
@patch("subprocess.run")
def test_start(mock_run, mock_popen, k8s_system):
    mock_run.return_value.stdout = "ok"
    # Mock Popen for port forwarding
    process_mock = MagicMock()
    process_mock.poll.return_value = None # Running
    mock_popen.return_value = process_mock
    
    k8s_system.start()
    
    # Verify helm install calls
    # We expect MinIO install and Trino install
    calls = mock_run.call_args_list
    
    # Check for MinIO install
    minio_install_found = False
    trino_install_found = False
    
    for call in calls:
        args = call[0][0]
        if "helm" in args and "install" in args:
            if "minio-release" in args:
                minio_install_found = True
            if "test-release" in args:
                trino_install_found = True
                
    assert minio_install_found
    assert trino_install_found
    
    # Check port forwarding
    assert mock_popen.called
    assert k8s_system.is_running is True

@patch("subprocess.run")
def test_stop(mock_run, k8s_system):
    mock_run.return_value.stdout = "ok"
    k8s_system._is_running = True
    
    # Mock the port forward process
    pf_mock = MagicMock()
    k8s_system._pf_process = pf_mock
    
    k8s_system.stop()
    
    # Should uninstall Trino and MinIO
    calls = mock_run.call_args_list
    uninstall_count = 0
    for call in calls:
        args = call[0][0]
        if "helm" in args and "uninstall" in args:
            uninstall_count += 1
            
    assert uninstall_count >= 2 # Trino and MinIO
    
    # Should terminate port forward
    assert pf_mock.terminate.called
    assert k8s_system.is_running is False
