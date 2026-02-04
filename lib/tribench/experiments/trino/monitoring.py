"""Monitoring integration for Trino experiments.

Handles setup and management of monitoring sessions during experiment execution.
"""

import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ...config import ConnectionConfig
    from ...monitoring import MonitoringSession, MonitoringConfig, TrinoMonitor

logger = logging.getLogger(__name__)

# Optional monitoring imports (graceful degradation if not available)
try:
    from ...monitoring import (
        MonitoringSession,
        MonitoringConfig,
        ResourceMonitor,
        TrinoMonitor,
        KubernetesPodMonitor,
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring module not available - experiments will run without monitoring")


def is_monitoring_available() -> bool:
    """Check if monitoring module is available."""
    return MONITORING_AVAILABLE


class ExperimentMonitoringMixin:
    """
    Mixin class providing monitoring capabilities for experiments.
    
    This mixin handles:
    - Monitoring session setup and teardown
    - Metric collection coordination
    - Query tracking integration
    
    Attributes expected from the host class:
    - config: ExperimentConfig
    - connection_config: ConnectionConfig
    - enable_monitoring: bool
    - monitoring_session: Optional[MonitoringSession]
    - trino_monitor: Optional[TrinoMonitor]
    """
    
    def _setup_monitoring(self, connection_config: 'ConnectionConfig', kubernetes_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Set up monitoring session with collectors.
        
        Args:
            connection_config: ConnectionConfig for Trino
            kubernetes_config: Optional Kubernetes monitoring configuration
        """
        if not MONITORING_AVAILABLE:
            logger.warning("Monitoring module not available")
            self.enable_monitoring = False
            return
            
        try:
            # Create monitoring config
            monitoring_config = MonitoringConfig(
                enabled=True,
                interval_seconds=1.0,  # 1 second sampling
            )
            
            # Create collectors
            collectors = []
            
            # Add resource monitor
            resource_monitor = ResourceMonitor(config=monitoring_config)
            collectors.append(resource_monitor)
            
            # Add Trino monitor
            self.trino_monitor = TrinoMonitor(
                config=monitoring_config,
                host=connection_config.host,
                port=connection_config.port,
                username=connection_config.user,
            )
            collectors.append(self.trino_monitor)
            
            # Add Kubernetes pod monitor if configured
            if kubernetes_config and kubernetes_config.get('enabled', False):
                try:
                    k8s_monitor = KubernetesPodMonitor(
                        config=monitoring_config,
                        context=kubernetes_config.get('context', 'kind-tribench'),
                        namespace=kubernetes_config.get('namespace', 'default'),
                        label_selector=kubernetes_config.get('label_selector'),
                        pod_name_pattern=kubernetes_config.get('pod_name_pattern')
                    )
                    collectors.append(k8s_monitor)
                    logger.info("Kubernetes pod monitoring enabled")
                except Exception as e:
                    logger.warning(f"Failed to initialize Kubernetes monitoring: {e}")
            
            # Create monitoring session
            self.monitoring_session = MonitoringSession(
                config=monitoring_config,
                collectors=collectors,
                experiment_name=self.config.name,
            )
            
            logger.info("Monitoring session initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring: {e}")
            self.enable_monitoring = False
            self.monitoring_session = None
            self.trino_monitor = None
    
    def _start_monitoring(self) -> None:
        """Start the monitoring session."""
        if self.enable_monitoring and self.monitoring_session:
            try:
                self.monitoring_session.start()
                logger.info("Monitoring started")
            except Exception as e:
                logger.error(f"Failed to start monitoring: {e}")
                self.enable_monitoring = False
    
    def _save_run_monitoring_metrics(self, run_id: int) -> int:
        """
        Save monitoring metrics collected so far for a specific run.
        
        Args:
            run_id: The run ID to save metrics for
            
        Returns:
            Number of metrics saved
        """
        if not self.enable_monitoring or not self.monitoring_session:
            return 0
        
        if not self.enable_database or not self.result_storage:
            return 0
        
        try:
            # Get all collected metrics from the monitoring session
            with self.monitoring_session._metrics_lock:
                all_metrics = self.monitoring_session._collected_metrics.copy()
                # Clear the collected metrics to avoid duplicates in next run
                self.monitoring_session._collected_metrics.clear()
            
            # Also collect any remaining metrics from collector buffers
            for collector in self.monitoring_session.collectors:
                if hasattr(collector, '_metrics_buffer') and collector._metrics_buffer:
                    all_metrics.extend(collector._metrics_buffer)
                    collector._metrics_buffer.clear()
            
            if all_metrics:
                saved_count = self.result_storage.save_monitoring_metrics(
                    run_id=run_id,
                    metrics=all_metrics
                )
                logger.info(f"Saved {saved_count} monitoring metrics for run {run_id}")
                return saved_count
            else:
                logger.debug(f"No monitoring metrics to save for run {run_id}")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to save monitoring metrics for run {run_id}: {e}")
            return 0
    
    def _stop_monitoring_and_collect(self, current_run_id: Optional[int] = None) -> Optional[str]:
        """
        Stop monitoring and collect/save any remaining metrics.
        
        Note: This is called at the end of the experiment. Individual run metrics
        should already be saved via _save_run_monitoring_metrics() after each run.
        This method only saves any remaining metrics that weren't captured per-run
        (e.g., from warmup runs or final cleanup).
        
        Args:
            current_run_id: Current run ID for database storage (last run)
            
        Returns:
            Path to monitoring file if JSON export enabled, None otherwise
        """
        if not self.enable_monitoring or not self.monitoring_session:
            return None
            
        monitoring_file = None
        
        try:
            self.monitoring_session.stop()
            
            # Get any remaining collected metrics from the monitoring session
            # (These would be from warmup runs or final cleanup period)
            with self.monitoring_session._metrics_lock:
                all_metrics = self.monitoring_session._collected_metrics.copy()
            
            # Also collect any remaining metrics from collector buffers
            for collector in self.monitoring_session.collectors:
                if hasattr(collector, '_metrics_buffer') and collector._metrics_buffer:
                    all_metrics.extend(collector._metrics_buffer)
            
            # Save remaining metrics to last run if any exist
            # Most metrics should already be saved per-run at this point
            if self.enable_database and self.result_storage and current_run_id and all_metrics:
                try:
                    saved_count = self.result_storage.save_monitoring_metrics(
                        run_id=current_run_id,
                        metrics=all_metrics
                    )
                    logger.info(f"Saved {saved_count} remaining monitoring metrics to run {current_run_id}")
                except Exception as e:
                    logger.error(f"Failed to save remaining monitoring metrics to database: {e}")
            
            # Save to JSON file only if enabled
            if getattr(self, 'enable_json', False):
                monitoring_file = self.monitoring_session.save_metrics()
                logger.info(f"Monitoring data saved to: {monitoring_file}")
            
        except Exception as e:
            logger.error(f"Failed to save monitoring data: {e}")
        
        return monitoring_file
    
    def _track_query_in_monitoring(self, query_id: Optional[str]) -> None:
        """
        Track a query in the Trino monitor.
        
        Args:
            query_id: Trino query ID to track
        """
        if not query_id:
            return
            
        if self.enable_monitoring and self.trino_monitor:
            try:
                self.trino_monitor.track_query(query_id)
            except Exception as e:
                logger.warning(f"Failed to track query in monitoring: {e}")
    
    def _get_monitoring_summary(self) -> dict:
        """Get monitoring summary for results."""
        if self.monitoring_session:
            return self.monitoring_session.get_summary()
        return {}


def is_monitoring_available() -> bool:
    """Check if monitoring module is available."""
    return MONITORING_AVAILABLE
