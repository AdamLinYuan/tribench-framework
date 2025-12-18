"""Query collection and validation for Trino experiments.

Handles query loading from files/inline and result validation.
"""

import logging
import statistics
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger(__name__)


def collect_queries(
    inline_queries: List,
    query_files: List[str],
    root_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Collect all queries from inline and file sources.
    
    Args:
        inline_queries: List of inline query strings or dicts
        query_files: List of query file paths
        root_path: Root path for resolving relative paths
        
    Returns:
        List of query dictionaries with 'sql', 'name', 'source' keys
    """
    queries = []
    
    # Add inline queries
    for idx, query in enumerate(inline_queries):
        if isinstance(query, str):
            queries.append({
                "name": f"query_{idx + 1}",
                "sql": query,
                "source": "inline",
            })
        elif isinstance(query, dict):
            queries.append({
                "name": query.get("name", f"query_{idx + 1}"),
                "sql": query["sql"],
                "source": "inline",
            })
        else:
            logger.warning(f"Skipping invalid query format: {type(query)}")
    
    # Add queries from files
    if root_path is None:
        root_path = Path(__file__).parent.parent.parent.parent.parent
    
    for query_file in query_files:
        query_path = Path(query_file)
        
        # If not absolute, try multiple resolution strategies
        if not query_path.is_absolute():
            resolved_path = root_path / query_file
            
            if not resolved_path.exists():
                resolved_path = root_path / "experiments" / query_file
            
            if not resolved_path.exists():
                logger.error(f"Query file not found: {query_file}")
                logger.error(f"  Tried: {root_path / query_file}")
                logger.error(f"  Tried: {root_path / 'experiments' / query_file}")
                continue
            
            query_path = resolved_path
        
        if not query_path.exists():
            logger.error(f"Query file not found: {query_path}")
            continue
        
        try:
            sql_content = query_path.read_text()
            queries.append({
                "name": query_path.stem,
                "sql": sql_content,
                "source": str(query_path),
            })
            logger.info(f"Loaded query from file: {query_path.name}")
        except Exception as e:
            logger.error(f"Failed to read query file {query_path}: {e}")
            continue
    
    return queries


def validate_results(
    executions: List,
    validation_rules: Dict[str, Any],
    get_status: Callable,
    get_time: Callable,
    status_success: str,
) -> bool:
    """
    Validate experiment results against rules.
    
    Args:
        executions: List of execution results
        validation_rules: Dictionary of validation rules
        get_status: Function to extract status from an execution
        get_time: Function to extract execution time from an execution
        status_success: Status value indicating success
        
    Returns:
        True if all validations pass, False otherwise
    """
    if not executions:
        logger.warning("No results to validate")
        return False
    
    # Check success rate
    min_success_rate = validation_rules.get("min_success_rate", 0.95)
    success_count = sum(1 for q in executions if get_status(q) == status_success)
    actual_success_rate = success_count / len(executions)
    
    logger.info(f"Validation: {success_count}/{len(executions)} succeeded ({actual_success_rate:.1%})")
    
    if actual_success_rate < min_success_rate:
        logger.error(
            f"Validation FAILED: Success rate {actual_success_rate:.2%} "
            f"below minimum {min_success_rate:.2%}"
        )
        return False
    
    # Check execution time variance
    max_variance = validation_rules.get("max_execution_time_variance", 0.2)
    successful_times = [
        get_time(q) for q in executions 
        if get_status(q) == status_success and get_time(q) is not None
    ]
    
    if len(successful_times) > 1:
        mean_time = statistics.mean(successful_times)
        stdev_time = statistics.stdev(successful_times)
        cv = stdev_time / mean_time if mean_time > 0 else 0
        
        if cv > max_variance:
            logger.warning(
                f"Execution time variance {cv:.2%} above maximum {max_variance:.2%}"
            )
    
    logger.info("Validation passed")
    return True
