"""
Trino monitoring implementation.

Collects Trino-specific metrics via REST API and JMX endpoints, including:
- Query execution metrics
- Cluster metrics
- Data processing metrics
- Resource usage per query
"""

import logging
import time
import requests
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from .base import MetricCollector, Metric, MonitoringConfig
from ..defaults import Defaults

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single Trino query."""
    
    query_id: str
    state: str
    query: str
    
    # Timing metrics (milliseconds)
    queued_time_ms: Optional[int] = None
    planning_time_ms: Optional[int] = None
    analysis_time_ms: Optional[int] = None
    execution_time_ms: Optional[int] = None
    elapsed_time_ms: Optional[int] = None
    
    # Resource metrics
    cpu_time_ms: Optional[int] = None
    scheduled_time_ms: Optional[int] = None
    blocked_time_ms: Optional[int] = None
    peak_memory_bytes: Optional[int] = None
    
    # Data processing metrics
    input_rows: Optional[int] = None
    input_bytes: Optional[int] = None
    output_rows: Optional[int] = None
    output_bytes: Optional[int] = None
    physical_input_bytes: Optional[int] = None
    
    # Query state
    create_time: Optional[str] = None
    end_time: Optional[str] = None
    user: Optional[str] = None
    session_properties: Dict[str, Any] = field(default_factory=dict)
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ClusterMetrics:
    """Metrics for Trino cluster state."""
    
    # Cluster information
    version: str
    coordinator: bool
    starting: bool
    
    # Query statistics
    active_queries: int = 0
    queued_queries: int = 0
    running_queries: int = 0
    blocked_queries: int = 0
    
    # Node statistics
    active_nodes: int = 0
    inactive_nodes: int = 0
    shutting_down_nodes: int = 0
    
    # Resource statistics
    total_available_processors: int = 0
    running_drivers: int = 0
    running_tasks: int = 0
    reserved_memory_bytes: int = 0


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
        self.base_url = f"{protocol}://{host}:{port}"
        
        # Authentication
        self.auth = (username, password) if username and password else None
        
        # Tracked queries
        self.tracked_queries: List[str] = []
        
        # Cache for cluster info (refreshed periodically)
        self._cluster_info_cache: Optional[ClusterMetrics] = None
        self._cluster_info_cache_time: float = 0
        self._cluster_info_cache_ttl: float = 5.0  # 5 seconds
        
        logger.info(f"Initialized Trino monitor for {self.base_url}")
    
    def start(self) -> None:
        """Start monitoring."""
        self.is_running = True
        
        # Verify connectivity
        try:
            self._check_connectivity()
            logger.info(f"Successfully connected to Trino at {self.base_url}")
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
            cluster_metrics = self._collect_cluster_metrics()
            if cluster_metrics:
                metrics.extend(self._convert_cluster_metrics(cluster_metrics, timestamp))
            
            # Collect query metrics for tracked queries
            for query_id in self.tracked_queries[:]:  # Copy list to allow modification
                try:
                    query_metrics = self._collect_query_metrics(query_id)
                    if query_metrics:
                        metrics.extend(self._convert_query_metrics(query_metrics, timestamp))
                        
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
        return self._collect_query_metrics(query_id)
    
    def get_query_plan(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Get query execution plan for a specific query.
        
        Args:
            query_id: Trino query ID
            
        Returns:
            Query plan as dictionary or None if not found
        """
        try:
            url = urljoin(self.base_url, f"/v1/query/{query_id}")
            response = requests.get(url, auth=self.auth, timeout=self.timeout)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Extract query plan information
            output_stage = data.get("outputStage")
            if not output_stage:
                return None
            
            return {
                "query_id": query_id,
                "root_stage": self._extract_stage_info(output_stage),
                "state": data.get("state"),
            }
        
        except Exception as e:
            logger.warning(f"Failed to get query plan for {query_id}: {e}")
            return None
    
    def get_stage_metrics(self, query_id: str) -> List[Dict[str, Any]]:
        """
        Get stage-level execution metrics for a query.
        
        Args:
            query_id: Trino query ID
            
        Returns:
            List of stage metrics dictionaries
        """
        try:
            url = urljoin(self.base_url, f"/v1/query/{query_id}")
            response = requests.get(url, auth=self.auth, timeout=self.timeout)
            
            if response.status_code == 404:
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Extract stage statistics
            output_stage = data.get("outputStage")
            if not output_stage:
                return []
            
            stages = []
            self._extract_stage_metrics(output_stage, stages)
            return stages
        
        except Exception as e:
            logger.warning(f"Failed to get stage metrics for {query_id}: {e}")
            return []
    
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
                user=self.auth[0] if self.auth else "trino",
                http_scheme="https" if "https" in self.base_url else "http",
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
    
    # Private methods
    
    def _check_connectivity(self) -> None:
        """Check connectivity to Trino coordinator."""
        url = urljoin(self.base_url, "/v1/info")
        response = requests.get(url, auth=self.auth, timeout=self.timeout)
        response.raise_for_status()
    
    def _collect_cluster_metrics(self) -> Optional[ClusterMetrics]:
        """
        Collect cluster-wide metrics.
        
        Returns:
            ClusterMetrics object or None if failed
        """
        # Check cache
        now = time.time()
        if (self._cluster_info_cache and 
            now - self._cluster_info_cache_time < self._cluster_info_cache_ttl):
            return self._cluster_info_cache
        
        try:
            # Get cluster info
            info_url = urljoin(self.base_url, "/v1/info")
            info_response = requests.get(info_url, auth=self.auth, timeout=self.timeout)
            info_response.raise_for_status()
            info_data = info_response.json()
            
            # Get cluster stats
            cluster_url = urljoin(self.base_url, "/v1/cluster")
            cluster_response = requests.get(cluster_url, auth=self.auth, timeout=self.timeout)
            cluster_response.raise_for_status()
            cluster_data = cluster_response.json()
            
            # Build ClusterMetrics
            metrics = ClusterMetrics(
                version=info_data.get("nodeVersion", {}).get("version", "unknown"),
                coordinator=info_data.get("coordinator", False),
                starting=info_data.get("starting", False),
            )
            
            # Extract cluster statistics
            if "runningQueries" in cluster_data:
                metrics.running_queries = cluster_data["runningQueries"]
            if "blockedQueries" in cluster_data:
                metrics.blocked_queries = cluster_data["blockedQueries"]
            if "queuedQueries" in cluster_data:
                metrics.queued_queries = cluster_data["queuedQueries"]
            if "activeWorkers" in cluster_data:
                metrics.active_nodes = cluster_data["activeWorkers"]
            if "runningDrivers" in cluster_data:
                metrics.running_drivers = cluster_data["runningDrivers"]
            if "runningTasks" in cluster_data:
                metrics.running_tasks = cluster_data["runningTasks"]
            if "reservedMemory" in cluster_data:
                metrics.reserved_memory_bytes = cluster_data["reservedMemory"]
            if "totalAvailableProcessors" in cluster_data:
                metrics.total_available_processors = cluster_data["totalAvailableProcessors"]
            
            # Update cache
            self._cluster_info_cache = metrics
            self._cluster_info_cache_time = now
            
            return metrics
        
        except requests.exceptions.HTTPError as e:
            # 404 is expected if cluster endpoint is not available in this Trino version
            if e.response.status_code == 404:
                logger.debug(f"Cluster metrics endpoint not available (404): {e}")
            else:
                logger.warning(f"Failed to collect cluster metrics: {e}")
            return None
        except Exception as e:
            logger.debug(f"Failed to collect cluster metrics: {e}")
            return None
    
    def _collect_query_metrics(self, query_id: str) -> Optional[QueryMetrics]:
        """
        Collect metrics for a specific query.
        
        Args:
            query_id: Trino query ID
            
        Returns:
            QueryMetrics object or None if not found
        """
        try:
            # Query endpoint: /v1/query/{queryId}
            url = urljoin(self.base_url, f"/v1/query/{query_id}")
            response = requests.get(url, auth=self.auth, timeout=self.timeout)
            
            if response.status_code == 404:
                logger.debug(f"Query not found: {query_id}")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Extract query info
            query_stats = data.get("queryStats", {})
            error_info = data.get("errorCode")
            
            metrics = QueryMetrics(
                query_id=data.get("queryId", query_id),
                state=data.get("state", "UNKNOWN"),
                query=data.get("query", ""),
                
                # Timing
                queued_time_ms=query_stats.get("queuedTime", {}).get("value"),
                planning_time_ms=query_stats.get("planningTime", {}).get("value"),
                analysis_time_ms=query_stats.get("analysisTime", {}).get("value"),
                execution_time_ms=query_stats.get("executionTime", {}).get("value"),
                elapsed_time_ms=query_stats.get("elapsedTime", {}).get("value"),
                
                # Resources
                cpu_time_ms=query_stats.get("totalCpuTime", {}).get("value"),
                scheduled_time_ms=query_stats.get("totalScheduledTime", {}).get("value"),
                blocked_time_ms=query_stats.get("totalBlockedTime", {}).get("value"),
                peak_memory_bytes=query_stats.get("peakMemoryReservation", {}).get("value"),
                
                # Data processing
                input_rows=query_stats.get("rawInputPositions"),
                input_bytes=query_stats.get("rawInputDataSize", {}).get("value"),
                output_rows=query_stats.get("outputPositions"),
                output_bytes=query_stats.get("outputDataSize", {}).get("value"),
                physical_input_bytes=query_stats.get("physicalInputDataSize", {}).get("value"),
                
                # Query state
                create_time=query_stats.get("createTime"),
                end_time=query_stats.get("endTime"),
                user=data.get("session", {}).get("user"),
                session_properties=data.get("session", {}).get("systemProperties", {}),
                
                # Error info
                error_code=error_info.get("name") if error_info else None,
                error_message=data.get("failureInfo", {}).get("message"),
            )
            
            return metrics
        
        except requests.exceptions.HTTPError as e:
            # 401/403 are expected if authentication is required but not configured
            # 404 is expected if query is not found or endpoint unavailable
            if e.response.status_code in (401, 403, 404):
                logger.debug(f"Query metrics unavailable for {query_id} ({e.response.status_code}): {e}")
            else:
                logger.warning(f"Failed to collect query metrics for {query_id}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Failed to collect query metrics for {query_id}: {e}")
            return None
    
    def _extract_stage_info(self, stage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract stage information recursively.
        
        Args:
            stage_data: Stage data from query API
            
        Returns:
            Dictionary with stage information
        """
        stage_info = {
            "stage_id": stage_data.get("stageId"),
            "state": stage_data.get("state"),
            "plan": stage_data.get("plan", {}).get("name"),
            "sub_stages": [],
        }
        
        # Extract statistics if available
        stats = stage_data.get("stageStats", {})
        if stats:
            stage_info["stats"] = {
                "total_tasks": stats.get("totalTasks"),
                "running_tasks": stats.get("runningTasks"),
                "completed_tasks": stats.get("completedTasks"),
                "total_drivers": stats.get("totalDrivers"),
                "queued_drivers": stats.get("queuedDrivers"),
                "running_drivers": stats.get("runningDrivers"),
                "completed_drivers": stats.get("completedDrivers"),
                "cumulative_memory_bytes": stats.get("cumulativeUserMemory", {}).get("value"),
                "peak_memory_bytes": stats.get("userMemoryReservation", {}).get("value"),
                "total_cpu_time_ms": stats.get("totalCpuTime", {}).get("value"),
                "total_scheduled_time_ms": stats.get("totalScheduledTime", {}).get("value"),
                "raw_input_positions": stats.get("rawInputPositions"),
                "raw_input_data_size_bytes": stats.get("rawInputDataSize", {}).get("value"),
                "processed_input_positions": stats.get("processedInputPositions"),
                "processed_input_data_size_bytes": stats.get("processedInputDataSize", {}).get("value"),
                "output_positions": stats.get("outputPositions"),
                "output_data_size_bytes": stats.get("outputDataSize", {}).get("value"),
            }
        
        # Recursively extract sub-stages
        sub_stages = stage_data.get("subStages", [])
        for sub_stage in sub_stages:
            stage_info["sub_stages"].append(self._extract_stage_info(sub_stage))
        
        return stage_info
    
    def _extract_stage_metrics(self, 
                               stage_data: Dict[str, Any], 
                               stages: List[Dict[str, Any]]) -> None:
        """
        Extract stage metrics recursively.
        
        Args:
            stage_data: Stage data from query API
            stages: List to append stage metrics to
        """
        stats = stage_data.get("stageStats", {})
        
        stage_metrics = {
            "stage_id": stage_data.get("stageId"),
            "state": stage_data.get("state"),
            "plan_node": stage_data.get("plan", {}).get("name"),
            
            # Task metrics
            "total_tasks": stats.get("totalTasks", 0),
            "running_tasks": stats.get("runningTasks", 0),
            "completed_tasks": stats.get("completedTasks", 0),
            
            # Driver metrics
            "total_drivers": stats.get("totalDrivers", 0),
            "queued_drivers": stats.get("queuedDrivers", 0),
            "running_drivers": stats.get("runningDrivers", 0),
            "completed_drivers": stats.get("completedDrivers", 0),
            
            # Resource metrics
            "cumulative_memory_bytes": stats.get("cumulativeUserMemory", {}).get("value", 0),
            "peak_memory_bytes": stats.get("userMemoryReservation", {}).get("value", 0),
            "total_cpu_time_ms": stats.get("totalCpuTime", {}).get("value", 0),
            "total_scheduled_time_ms": stats.get("totalScheduledTime", {}).get("value", 0),
            
            # Data metrics
            "raw_input_rows": stats.get("rawInputPositions", 0),
            "raw_input_bytes": stats.get("rawInputDataSize", {}).get("value", 0),
            "processed_input_rows": stats.get("processedInputPositions", 0),
            "processed_input_bytes": stats.get("processedInputDataSize", {}).get("value", 0),
            "output_rows": stats.get("outputPositions", 0),
            "output_bytes": stats.get("outputDataSize", {}).get("value", 0),
        }
        
        stages.append(stage_metrics)
        
        # Recursively process sub-stages
        sub_stages = stage_data.get("subStages", [])
        for sub_stage in sub_stages:
            self._extract_stage_metrics(sub_stage, stages)
    
    def _convert_cluster_metrics(self, 
                                 cluster: ClusterMetrics, 
                                 timestamp: datetime) -> List[Metric]:
        """
        Convert ClusterMetrics to list of Metric objects.
        
        Args:
            cluster: ClusterMetrics object
            timestamp: Collection timestamp
            
        Returns:
            List of Metric objects
        """
        labels = {
            "source": "trino_cluster",
            "version": cluster.version,
        }
        
        return [
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.queries.running",
                value=cluster.running_queries,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.queries.queued",
                value=cluster.queued_queries,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.queries.blocked",
                value=cluster.blocked_queries,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.nodes.active",
                value=cluster.active_nodes,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.drivers.running",
                value=cluster.running_drivers,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.tasks.running",
                value=cluster.running_tasks,
                unit="count",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.memory.reserved",
                value=cluster.reserved_memory_bytes,
                unit="bytes",
                labels=labels,
            ),
            Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.cluster.processors.available",
                value=cluster.total_available_processors,
                unit="count",
                labels=labels,
            ),
        ]
    
    def _convert_query_metrics(self,
                              query: QueryMetrics,
                              timestamp: datetime) -> List[Metric]:
        """
        Convert QueryMetrics to list of Metric objects.
        
        Args:
            query: QueryMetrics object
            timestamp: Collection timestamp
            
        Returns:
            List of Metric objects
        """
        labels = {
            "source": "trino_query",
            "query_id": query.query_id,
            "state": query.state,
            "user": query.user or "unknown",
        }
        
        metrics = []
        
        # Timing metrics
        if query.queued_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.time.queued",
                value=query.queued_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.planning_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.time.planning",
                value=query.planning_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.execution_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.time.execution",
                value=query.execution_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.elapsed_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.time.elapsed",
                value=query.elapsed_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        # Resource metrics
        if query.cpu_time_ms is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.cpu_time",
                value=query.cpu_time_ms,
                unit="milliseconds",
                labels=labels,
            ))
        
        if query.peak_memory_bytes is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.memory.peak",
                value=query.peak_memory_bytes,
                unit="bytes",
                labels=labels,
            ))
        
        # Data processing metrics
        if query.input_rows is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.data.input.rows",
                value=query.input_rows,
                unit="count",
                labels=labels,
            ))
        
        if query.input_bytes is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.data.input.bytes",
                value=query.input_bytes,
                unit="bytes",
                labels=labels,
            ))
        
        if query.output_rows is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.data.output.rows",
                value=query.output_rows,
                unit="count",
                labels=labels,
            ))
        
        if query.output_bytes is not None:
            metrics.append(Metric(
                timestamp=timestamp,
                type="gauge",
                name="trino.query.data.output.bytes",
                value=query.output_bytes,
                unit="bytes",
                labels=labels,
            ))
        
        return metrics
