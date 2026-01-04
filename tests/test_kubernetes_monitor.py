"""
Unit tests for KubernetesPodMonitor.

Tests kubectl command execution, metric parsing, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import subprocess

from tribench.monitoring.kubernetes_monitor import (
    KubernetesPodMonitor,
    PodMetrics
)
from tribench.monitoring.base import MonitoringConfig


class TestKubernetesPodMonitor:
    """Tests for KubernetesPodMonitor class."""
    
    @pytest.fixture
    def config(self):
        """Create monitoring configuration."""
        return MonitoringConfig(
            enabled=True,
            interval_seconds=5.0,
            collect_system_resources=True
        )
    
    @pytest.fixture
    def monitor(self, config):
        """Create KubernetesPodMonitor instance."""
        return KubernetesPodMonitor(
            config=config,
            context="kind-tribench",
            namespace="default",
            label_selector="app=trino"
        )
    
    def test_init(self, monitor):
        """Test monitor initialization."""
        assert monitor.context == "kind-tribench"
        assert monitor.namespace == "default"
        assert monitor.label_selector == "app=trino"
        assert not monitor._metrics_server_available
    
    def test_parse_cpu_millicores(self, monitor):
        """Test parsing CPU in millicores."""
        millicores, cores = monitor._parse_cpu("150m")
        assert millicores == 150
        assert cores == 0.15
    
    def test_parse_cpu_cores(self, monitor):
        """Test parsing CPU in cores."""
        millicores, cores = monitor._parse_cpu("2")
        assert millicores == 2000
        assert cores == 2.0
    
    def test_parse_cpu_large_millicores(self, monitor):
        """Test parsing large millicores value."""
        millicores, cores = monitor._parse_cpu("1500m")
        assert millicores == 1500
        assert cores == 1.5
    
    def test_parse_cpu_invalid(self, monitor):
        """Test parsing invalid CPU value."""
        millicores, cores = monitor._parse_cpu("invalid")
        assert millicores is None
        assert cores is None
    
    def test_parse_memory_mi(self, monitor):
        """Test parsing memory in Mi (mebibytes)."""
        bytes_val, mb_val, gb_val = monitor._parse_memory("2048Mi")
        assert bytes_val == 2048 * 1024 * 1024
        assert mb_val == pytest.approx(2048.0)
        assert gb_val == pytest.approx(2.0)
    
    def test_parse_memory_gi(self, monitor):
        """Test parsing memory in Gi (gibibytes)."""
        bytes_val, mb_val, gb_val = monitor._parse_memory("1Gi")
        assert bytes_val == 1024 * 1024 * 1024
        assert mb_val == pytest.approx(1024.0)
        assert gb_val == pytest.approx(1.0)
    
    def test_parse_memory_ki(self, monitor):
        """Test parsing memory in Ki (kibibytes)."""
        bytes_val, mb_val, gb_val = monitor._parse_memory("512Ki")
        assert bytes_val == 512 * 1024
        assert mb_val == pytest.approx(0.5)
        assert gb_val < 0.001
    
    def test_parse_memory_decimal(self, monitor):
        """Test parsing memory with decimal value."""
        bytes_val, mb_val, gb_val = monitor._parse_memory("1.5Gi")
        assert bytes_val == int(1.5 * 1024 * 1024 * 1024)
        assert mb_val == pytest.approx(1536.0)
        assert gb_val == pytest.approx(1.5)
    
    def test_parse_memory_invalid(self, monitor):
        """Test parsing invalid memory value."""
        bytes_val, mb_val, gb_val = monitor._parse_memory("invalid")
        assert bytes_val is None
        assert mb_val is None
        assert gb_val is None
    
    def test_extract_pod_labels_coordinator(self, monitor):
        """Test extracting labels from coordinator pod name."""
        labels = monitor._extract_pod_labels("trino-coordinator-abc123")
        assert labels['component'] == 'coordinator'
        assert labels['role'] == 'coordinator'
        assert labels['system'] == 'trino'
    
    def test_extract_pod_labels_worker(self, monitor):
        """Test extracting labels from worker pod name."""
        labels = monitor._extract_pod_labels("trino-worker-1-def456")
        assert labels['component'] == 'worker'
        assert labels['role'] == 'worker'
        assert labels['system'] == 'trino'
    
    def test_extract_pod_labels_minio(self, monitor):
        """Test extracting labels from MinIO pod name."""
        labels = monitor._extract_pod_labels("minio-deployment-xyz789")
        assert labels['system'] == 'minio'
    
    def test_extract_pod_labels_postgres(self, monitor):
        """Test extracting labels from PostgreSQL pod name."""
        labels = monitor._extract_pod_labels("postgres-db-abc123")
        assert labels['system'] == 'postgres'
    
    def test_parse_kubectl_top_output(self, monitor):
        """Test parsing kubectl top pods output."""
        output = """NAME                              CPU(cores)   MEMORY(bytes)
trino-coordinator-abc123          150m         2048Mi
trino-worker-1-def456             500m         4096Mi
trino-worker-2-ghi789             450m         3584Mi"""
        
        timestamp = datetime.now()
        pod_metrics = monitor._parse_kubectl_top_output(output, timestamp)
        
        assert len(pod_metrics) == 3
        
        # Check coordinator
        coord = pod_metrics[0]
        assert coord.pod_name == "trino-coordinator-abc123"
        assert coord.cpu_millicores == 150
        assert coord.cpu_cores == 0.15
        assert coord.memory_mb == pytest.approx(2048.0)
        assert coord.labels['component'] == 'coordinator'
        
        # Check worker 1
        worker1 = pod_metrics[1]
        assert worker1.pod_name == "trino-worker-1-def456"
        assert worker1.cpu_millicores == 500
        assert worker1.cpu_cores == 0.5
        assert worker1.memory_mb == pytest.approx(4096.0)
        assert worker1.labels['component'] == 'worker'
    
    def test_parse_kubectl_top_output_empty(self, monitor):
        """Test parsing empty kubectl output."""
        output = "NAME                              CPU(cores)   MEMORY(bytes)"
        timestamp = datetime.now()
        pod_metrics = monitor._parse_kubectl_top_output(output, timestamp)
        assert len(pod_metrics) == 0
    
    def test_parse_kubectl_top_output_with_pattern_filter(self, monitor):
        """Test parsing with pod name pattern filtering."""
        monitor.pod_name_pattern = r"worker"
        
        output = """NAME                              CPU(cores)   MEMORY(bytes)
trino-coordinator-abc123          150m         2048Mi
trino-worker-1-def456             500m         4096Mi
minio-deployment-xyz789           100m         1024Mi"""
        
        timestamp = datetime.now()
        pod_metrics = monitor._parse_kubectl_top_output(output, timestamp)
        
        # Should only include worker pod
        assert len(pod_metrics) == 1
        assert pod_metrics[0].pod_name == "trino-worker-1-def456"
    
    def test_pod_metrics_to_metrics(self):
        """Test converting PodMetrics to Metric objects."""
        pod_metrics = PodMetrics(
            timestamp=datetime.now(),
            pod_name="trino-coordinator-abc123",
            namespace="default",
            cpu_millicores=150,
            cpu_cores=0.15,
            memory_bytes=2147483648,
            memory_mb=2048.0,
            memory_gb=2.0,
            labels={"component": "coordinator", "system": "trino"}
        )
        
        metrics = pod_metrics.to_metrics()
        
        # Should create 5 metrics: cpu_millicores, cpu_cores, memory_bytes, memory_mb, memory_gb
        assert len(metrics) == 5
        
        # Check metric names
        metric_names = [m.name for m in metrics]
        assert "pod_cpu_millicores" in metric_names
        assert "pod_cpu_cores" in metric_names
        assert "pod_memory_bytes" in metric_names
        assert "pod_memory_mb" in metric_names
        assert "pod_memory_gb" in metric_names
        
        # Check labels propagation
        for metric in metrics:
            assert metric.labels['pod'] == 'trino-coordinator-abc123'
            assert metric.labels['namespace'] == 'default'
            assert metric.labels['component'] == 'coordinator'
            assert metric.labels['system'] == 'trino'
    
    @patch('subprocess.run')
    def test_start_success(self, mock_run, monitor):
        """Test successful monitor start."""
        # Mock kubectl version check
        mock_run.side_effect = [
            Mock(returncode=0),  # kubectl version
            Mock(returncode=0),  # cluster-info
            Mock(returncode=0, stdout="", stderr="")  # top pods (metrics-server check)
        ]
        
        monitor.start()
        
        assert monitor.enabled
        assert monitor._metrics_server_available
    
    @patch('subprocess.run')
    def test_start_kubectl_not_found(self, mock_run, monitor):
        """Test start with kubectl not installed."""
        mock_run.side_effect = FileNotFoundError("kubectl not found")
        
        monitor.start()
        
        assert not monitor.enabled
    
    @patch('subprocess.run')
    def test_start_cluster_not_accessible(self, mock_run, monitor):
        """Test start with cluster not accessible."""
        mock_run.side_effect = [
            Mock(returncode=0),  # kubectl version
            subprocess.CalledProcessError(1, "kubectl", stderr="connection refused")  # cluster-info
        ]
        
        monitor.start()
        
        assert not monitor.enabled
    
    @patch('subprocess.run')
    def test_start_metrics_server_missing(self, mock_run, monitor):
        """Test start with metrics-server not deployed."""
        mock_run.side_effect = [
            Mock(returncode=0),  # kubectl version
            Mock(returncode=0),  # cluster-info
            Mock(returncode=1, stdout="", stderr="error: Metrics API not available")  # top pods
        ]
        
        monitor.start()
        
        assert not monitor.enabled
        assert not monitor._metrics_server_available
    
    @patch('subprocess.run')
    def test_collect_success(self, mock_run, monitor):
        """Test successful metric collection."""
        monitor.enabled = True
        monitor._metrics_server_available = True
        
        kubectl_output = """NAME                              CPU(cores)   MEMORY(bytes)
trino-coordinator-abc123          150m         2048Mi
trino-worker-1-def456             500m         4096Mi"""
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=kubectl_output
        )
        
        metrics = monitor.collect()
        
        # Should have metrics for 2 pods x 5 metrics each
        assert len(metrics) == 10
        
        # Verify kubectl command was called correctly
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "kubectl" in cmd
        assert "--context" in cmd
        assert "kind-tribench" in cmd
        assert "--namespace" in cmd
        assert "default" in cmd
        assert "top" in cmd
        assert "pods" in cmd
        assert "--selector" in cmd
        assert "app=trino" in cmd
    
    @patch('subprocess.run')
    def test_collect_disabled(self, mock_run, monitor):
        """Test collection when monitor is disabled."""
        monitor.enabled = False
        
        metrics = monitor.collect()
        
        assert len(metrics) == 0
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_collect_kubectl_error(self, mock_run, monitor):
        """Test collection with kubectl command error."""
        monitor.enabled = True
        monitor._metrics_server_available = True
        
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "kubectl", stderr="error: pods not found"
        )
        
        metrics = monitor.collect()
        
        assert len(metrics) == 0
    
    @patch('subprocess.run')
    def test_get_pod_list(self, mock_run, monitor):
        """Test getting list of monitored pods."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""pod/trino-coordinator-abc123
pod/trino-worker-1-def456
pod/trino-worker-2-ghi789"""
        )
        
        pods = monitor.get_pod_list()
        
        assert len(pods) == 3
        assert "trino-coordinator-abc123" in pods
        assert "trino-worker-1-def456" in pods
        assert "trino-worker-2-ghi789" in pods
    
    @patch('subprocess.run')
    def test_get_pod_list_with_pattern(self, mock_run, monitor):
        """Test getting pod list with pattern filter."""
        monitor.pod_name_pattern = r"worker"
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""pod/trino-coordinator-abc123
pod/trino-worker-1-def456
pod/trino-worker-2-ghi789"""
        )
        
        pods = monitor.get_pod_list()
        
        assert len(pods) == 2
        assert "trino-worker-1-def456" in pods
        assert "trino-worker-2-ghi789" in pods
        assert "trino-coordinator-abc123" not in pods
