"""
Trino monitoring implementation.

Main orchestrator for Trino metrics collection and query tracking.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from tribench.monitoring.base import MetricCollector, Metric, MonitoringConfig
from tribench.defaults import Defaults

from .api_client import TrinoAPIClient
from .models import QueryMetrics, ClusterMetrics
from .metrics_converter import MetricsConverter

logger = logging.getLogger(__name__)


class TrinoMonitor(MetricCollector):
    """
    Collects metrics from Trino via REST API.
    
    Connects to Trino coordinator's HTTP API to collect:
    - Query execution metrics from /v1/query/{queryId}
    - Cluster metrics from /v1/cluster
    - System metrics from /v1/info
    """
    
    def __init__(self,
                 config: MonitoringConfig,
                 host: str = Defaults.Trino.HOST,
                 port: int = Defaults.Trino.PORT,
                 use_https: bool = False,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 timeout: int = 10):
        """
        Initialize Trino monitor.
        
        Args:
            config: Monitoring configuration
            host: Trino coordinator hostname
            port: Trino coordinator HTTP port
            use_https: Use HTTPS instead of HTTP
            username: Username for authentication (optional)
            password: Password for authentication (optional)
            timeout: Request timeout in seconds
        """
        super().__init__(config)
        
        self.host = host
        self.port = port
        self.timeout = timeout
        self.is_running = False
        
        # Build base URL
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{host}:{port}"
        
        # Authentication
        auth = (username, password) if username and password else None
        
        # Initialize API client
        self.api_client = TrinoAPIClient(base_url, auth, timeout)
        
        # Tracked queries
        self.tracked_queries: List[str] = []
        
        logger.info(f"Initialized Trino monitor for {base_url}")
    
    def start(self) -> None:
        """Start monitoring."""
        self.is_running = True
        
        # Verify connectivity
        try:
            self.api_client.check_connectivity()
            logger.info(f"Successfully connected to Trino")
        except Exception as e:
            logger.error(f"Failed to connect to Trino: {e}")
            self.is_running = False
            raise
    
    def stop(self) -> None:
        """Stop monitoring."""
        self.is_running = False
        self.tracked_queries.clear()
        logger.info("Stopped Trino monitoring")
    
    def collect(self) -> List[Metric]:
        """
        Collect current Trino metrics.
        
        Returns:
            List of metrics collected
        """
        if not self.is_running:
            return []
        
        metrics = []
        timestamp = datetime.now()
        
        try:
            # Collect cluster metrics
            cluster_metrics = self.api_client.get_cluster_metrics()
            if cluster_metrics:
                metrics.extend(
                    MetricsConverter.convert_cluster_metrics(cluster_metrics, timestamp)
                )
            
            # Collect query metrics for tracked queries
            for query_id in self.tracked_queries[:]:  # Copy list to allow modification
                try:
                    query_metrics = self.api_client.get_query_metrics(query_id)
                    if query_metrics:
                        metrics.extend(
                            MetricsConverter.convert_query_metrics(query_metrics, timestamp)
                        )
                        
                        # Remove completed/failed queries from tracking
                        if query_metrics.state in ['FINISHED', 'FAILED', 'CANCELED']:
                            self.tracked_queries.remove(query_id)
                            logger.debug(f"Stopped tracking completed query: {query_id}")
                
                except Exception as e:
                    logger.warning(f"Failed to collect metrics for query {query_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting Trino metrics: {e}", exc_info=True)
        
        return metrics
    
    def track_query(self, query_id: str) -> None:
        """
        Start tracking a specific query.
        
        Args:
            query_id: Trino query ID to track
        """
        if query_id not in self.tracked_queries:
            self.tracked_queries.append(query_id)
            logger.debug(f"Now tracking query: {query_id}")
    
    def untrack_query(self, query_id: str) -> None:
        """
        Stop tracking a specific query.
        
        Args:
            query_id: Trino query ID to stop tracking
        """
        if query_id in self.tracked_queries:
            self.tracked_queries.remove(query_id)
            logger.debug(f"Stopped tracking query: {query_id}")
    
    def get_query_metrics(self, query_id: str) -> Optional[QueryMetrics]:
        """
        Get metrics for a specific query.
        
        Args:
            query_id: Trino query ID
            
        Returns:
            QueryMetrics object or None if not found
        """
        return self.api_client.get_query_metrics(query_id)
    
    def get_query_plan(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Get query execution plan for a specific query.
        
        Args:
            query_id: Trino query ID
            
        Returns:
            Query plan as dictionary or None if not found
        """
        return self.api_client.get_query_plan(query_id)
    
    def get_stage_metrics(self, query_id: str) -> List[Dict[str, Any]]:
        """
        Get stage-level execution metrics for a query.
        
        Args:
            query_id: Trino query ID
            
        Returns:
            List of stage metrics dictionaries
        """
        return self.api_client.get_stage_metrics(query_id)
    
    def explain_query(self, query: str, query_type: str = "LOGICAL") -> Optional[str]:
        """
        Get the execution plan for a query using EXPLAIN.
        
        Args:
            query: SQL query to explain
            query_type: Type of plan ('LOGICAL', 'DISTRIBUTED', 'VALIDATE', 'IO')
            
        Returns:
            Explanation text or None if failed
        """
        try:
            # Execute EXPLAIN query
            explain_query = f"EXPLAIN ({query_type}) {query}"
            
            # Create a temporary connection for EXPLAIN
            import trino
            conn = trino.dbapi.connect(
                host=self.host,
                port=self.port,
                user="trino",
                http_scheme="https" if self.api_client.base_url.startswith("https") else "http",
            )
            
            cursor = conn.cursor()
            cursor.execute(explain_query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Combine results into single text
            explanation = "\n".join(row[0] for row in results)
            return explanation
        
        except Exception as e:
            logger.warning(f"Failed to explain query: {e}")
            return None
