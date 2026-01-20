"""
Trino REST API client.

Handles HTTP communication with Trino coordinator.
"""

import logging
import time
import requests
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin

from .models import QueryMetrics, ClusterMetrics

logger = logging.getLogger(__name__)


def _safe_get_value(data: Any, default=None) -> Union[int, float, None]:
    """Safely extract value that might be a float/int or dict with 'value' key."""
    if data is None:
        return default
    if isinstance(data, (int, float)):
        return data
    if isinstance(data, dict):
        return data.get('value', default)
    return default


class TrinoAPIClient:
    """Client for Trino REST API."""
    
    def __init__(self, 
                 base_url: str,
                 auth: Optional[tuple] = None,
                 user: Optional[str] = None,
                 timeout: int = 10):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for Trino coordinator
            auth: Optional (username, password) tuple for HTTP basic auth (deprecated)
            user: Trino user for X-Trino-User header (recommended)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.auth = auth
        self.timeout = timeout
        
        # Trino uses X-Trino-User header for authentication
        self.headers = {}
        if user:
            self.headers['X-Trino-User'] = user
        elif auth and auth[0]:
            self.headers['X-Trino-User'] = auth[0]
        
        # Cache for cluster info
        self._cluster_cache: Optional[ClusterMetrics] = None
        self._cluster_cache_time: float = 0
        self._cluster_cache_ttl: float = 5.0  # 5 seconds
    
    def check_connectivity(self) -> None:
        """
        Check connectivity to Trino coordinator.
        
        Raises:
            requests.exceptions.RequestException: If connection fails
        """
        url = urljoin(self.base_url, "/v1/info")
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
    
    def get_cluster_metrics(self) -> Optional[ClusterMetrics]:
        """
        Get cluster-wide metrics with caching.
        
        Returns:
            ClusterMetrics object or None if failed
        """
        # Check cache
        now = time.time()
        if (self._cluster_cache and 
            now - self._cluster_cache_time < self._cluster_cache_ttl):
            return self._cluster_cache
        
        try:
            # Get cluster info
            info_url = urljoin(self.base_url, "/v1/info")
            info_response = requests.get(info_url, headers=self.headers, timeout=self.timeout)
            info_response.raise_for_status()
            info_data = info_response.json()
            
            # Get cluster stats
            cluster_url = urljoin(self.base_url, "/v1/cluster")
            cluster_response = requests.get(cluster_url, headers=self.headers, timeout=self.timeout)
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
            self._cluster_cache = metrics
            self._cluster_cache_time = now
            
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
    
    def get_query_metrics(self, query_id: str) -> Optional[QueryMetrics]:
        """
        Get metrics for a specific query.
        
        Args:
            query_id: Trino query ID
            
        Returns:
            QueryMetrics object or None if not found
        """
        try:
            # Query endpoint: /v1/query/{queryId}
            url = urljoin(self.base_url, f"/v1/query/{query_id}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
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
                
                # Timing - safely handle both float and dict responses
                queued_time_ms=_safe_get_value(query_stats.get("queuedTime")),
                planning_time_ms=_safe_get_value(query_stats.get("planningTime")),
                analysis_time_ms=_safe_get_value(query_stats.get("analysisTime")),
                execution_time_ms=_safe_get_value(query_stats.get("executionTime")),
                elapsed_time_ms=_safe_get_value(query_stats.get("elapsedTime")),
                
                # Resources
                cpu_time_ms=_safe_get_value(query_stats.get("totalCpuTime")),
                scheduled_time_ms=_safe_get_value(query_stats.get("totalScheduledTime")),
                blocked_time_ms=_safe_get_value(query_stats.get("totalBlockedTime")),
                peak_memory_bytes=_safe_get_value(query_stats.get("peakMemoryReservation")),
                
                # Data processing
                input_rows=query_stats.get("rawInputPositions"),
                input_bytes=_safe_get_value(query_stats.get("rawInputDataSize")),
                output_rows=query_stats.get("outputPositions"),
                output_bytes=_safe_get_value(query_stats.get("outputDataSize")),
                physical_input_bytes=_safe_get_value(query_stats.get("physicalInputDataSize")),
                
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
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
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
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
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
    
    def _extract_stage_info(self, stage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract stage information recursively."""
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
                "cumulative_memory_bytes": _safe_get_value(stats.get("cumulativeUserMemory")),
                "peak_memory_bytes": _safe_get_value(stats.get("userMemoryReservation")),
                "total_cpu_time_ms": _safe_get_value(stats.get("totalCpuTime")),
                "total_scheduled_time_ms": _safe_get_value(stats.get("totalScheduledTime")),
                "raw_input_positions": stats.get("rawInputPositions"),
                "raw_input_data_size_bytes": _safe_get_value(stats.get("rawInputDataSize")),
                "processed_input_positions": stats.get("processedInputPositions"),
                "processed_input_data_size_bytes": _safe_get_value(stats.get("processedInputDataSize")),
                "output_positions": stats.get("outputPositions"),
                "output_data_size_bytes": _safe_get_value(stats.get("outputDataSize")),
            }
        
        # Recursively extract sub-stages
        sub_stages = stage_data.get("subStages", [])
        for sub_stage in sub_stages:
            stage_info["sub_stages"].append(self._extract_stage_info(sub_stage))
        
        return stage_info
    
    def _extract_stage_metrics(self, 
                               stage_data: Dict[str, Any], 
                               stages: List[Dict[str, Any]]) -> None:
        """Extract stage metrics recursively."""
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
            
            # Resource metrics - safely handle both float and dict
            "cumulative_memory_bytes": _safe_get_value(stats.get("cumulativeUserMemory"), 0),
            "peak_memory_bytes": _safe_get_value(stats.get("userMemoryReservation"), 0),
            "total_cpu_time_ms": _safe_get_value(stats.get("totalCpuTime"), 0),
            "total_scheduled_time_ms": _safe_get_value(stats.get("totalScheduledTime"), 0),
            
            # Data metrics
            "raw_input_rows": stats.get("rawInputPositions", 0),
            "raw_input_bytes": _safe_get_value(stats.get("rawInputDataSize"), 0),
            "processed_input_rows": stats.get("processedInputPositions", 0),
            "processed_input_bytes": _safe_get_value(stats.get("processedInputDataSize"), 0),
            "output_rows": stats.get("outputPositions", 0),
            "output_bytes": _safe_get_value(stats.get("outputDataSize"), 0),
        }
        
        stages.append(stage_metrics)
        
        # Recursively process sub-stages
        sub_stages = stage_data.get("subStages", [])
        for sub_stage in sub_stages:
            self._extract_stage_metrics(sub_stage, stages)
    
    def get_worker_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all Trino workers.
        
        Returns:
            List of worker information dictionaries with stats
        """
        try:
            # Get worker info from /v1/node endpoint
            url = urljoin(self.base_url, "/v1/node")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 404:
                logger.debug("Worker info endpoint not available (404)")
                return []
            
            response.raise_for_status()
            nodes_data = response.json()
            
            if not nodes_data or not isinstance(nodes_data, list):
                return []
            
            workers = []
            for idx, node in enumerate(nodes_data):
                if not isinstance(node, dict):
                    continue
                    
                worker_info = {
                    "node_id": node.get("nodeIdentifier") or node.get("uri", f"node-{idx}"),
                    "uri": node.get("uri"),
                    "version": node.get("nodeVersion"),
                    "state": node.get("state", "ACTIVE" if node.get("lastResponseTime") else "UNKNOWN"),
                    "coordinator": node.get("coordinator", False),
                    "last_response_time": node.get("lastResponseTime"),
                    "age": node.get("age"),
                    "recent_requests": node.get("recentRequests"),
                    "recent_failures": node.get("recentFailures"),
                    "recent_successes": node.get("recentSuccesses"),
                }
                
                # Extract memory pool information if available
                memory_info = node.get("memoryInfo")
                if memory_info and isinstance(memory_info, dict):
                    pools = memory_info.get("pools", {})
                    worker_info["memory"] = {
                        "total_bytes": _safe_get_value(memory_info.get("totalNodeMemory")),
                        "available_bytes": _safe_get_value(memory_info.get("availableNodeMemory")),
                    }
                    
                    # Extract pool-specific info
                    for pool_name, pool_data in pools.items():
                        if isinstance(pool_data, dict):
                            worker_info["memory"][f"{pool_name}_bytes"] = _safe_get_value(pool_data.get("maxBytes"))
                            worker_info["memory"][f"{pool_name}_reserved_bytes"] = _safe_get_value(pool_data.get("reservedBytes"))
                            worker_info["memory"][f"{pool_name}_free_bytes"] = _safe_get_value(pool_data.get("freeBytes"))
                
                workers.append(worker_info)
            
            return workers
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"Worker info endpoint not available (404): {e}")
            else:
                logger.warning(f"Failed to collect worker info: {e}")
            return []
        except Exception as e:
            logger.debug(f"Failed to collect worker info: {e}")
            return []
