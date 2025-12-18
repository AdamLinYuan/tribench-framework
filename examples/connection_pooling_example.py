#!/usr/bin/env python3
"""
Example demonstrating connection pooling for concurrent query execution.

This example shows how to use ConnectionPool to execute multiple queries
concurrently with efficient connection reuse.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from tribench.config import ConnectionConfig, ConnectionPool
from tribench.experiments.query_executor import QueryExecutor


def example_sequential_execution():
    """Example of sequential query execution (without pooling)."""
    print("=" * 60)
    print("Example 1: Sequential Execution (No Pooling)")
    print("=" * 60)
    
    config = ConnectionConfig.from_defaults()
    executor = QueryExecutor(connection=config)
    
    queries = [
        "SELECT 1 AS value",
        "SELECT 2 AS value",
        "SELECT 3 AS value",
        "SELECT 4 AS value",
        "SELECT 5 AS value",
    ]
    
    start_time = time.time()
    results = []
    
    with executor:
        for i, query in enumerate(queries, 1):
            print(f"\nExecuting query {i}/{len(queries)}: {query}")
            rows, metadata = executor.execute_query(query)
            results.append((rows, metadata))
            print(f"  ✓ Completed in {metadata['execution_time_seconds']:.3f}s")
    
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Total sequential execution time: {total_time:.3f}s")
    print(f"Average time per query: {total_time / len(queries):.3f}s")
    print(f"{'='*60}\n")
    
    return results


def example_concurrent_execution_with_pool():
    """Example of concurrent query execution with connection pooling."""
    print("=" * 60)
    print("Example 2: Concurrent Execution with Connection Pool")
    print("=" * 60)
    
    config = ConnectionConfig.from_defaults()
    executor = QueryExecutor(connection=config)
    
    # Create connection pool with 3 connections
    pool_size = 3
    print(f"\nCreating connection pool with size={pool_size}")
    
    queries = [
        "SELECT 1 AS value",
        "SELECT 2 AS value",
        "SELECT 3 AS value",
        "SELECT 4 AS value",
        "SELECT 5 AS value",
    ]
    
    start_time = time.time()
    results = []
    
    with ConnectionPool(config, pool_size=pool_size) as pool:
        print(f"Pool created: {pool.get_stats()}\n")
        
        # Execute queries concurrently using thread pool
        with ThreadPoolExecutor(max_workers=pool_size) as thread_pool:
            # Submit all queries
            futures = {
                thread_pool.submit(
                    executor.execute_with_pool, query, pool, True
                ): i for i, query in enumerate(queries, 1)
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                query_num = futures[future]
                try:
                    rows, metadata = future.result()
                    results.append((rows, metadata))
                    print(f"Query {query_num} completed in "
                          f"{metadata['execution_time_seconds']:.3f}s")
                except Exception as e:
                    print(f"Query {query_num} failed: {e}")
        
        print(f"\nFinal pool stats: {pool.get_stats()}")
    
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Total concurrent execution time: {total_time:.3f}s")
    print(f"Average time per query: {total_time / len(queries):.3f}s")
    print(f"Speedup vs sequential: {len(queries) / (total_time / 0.1):.2f}x")
    print(f"{'='*60}\n")
    
    return results


def example_pool_reuse():
    """Example showing connection reuse within a pool."""
    print("=" * 60)
    print("Example 3: Connection Reuse Demonstration")
    print("=" * 60)
    
    config = ConnectionConfig.from_defaults()
    executor = QueryExecutor(connection=config)
    
    # Small pool with many queries to force reuse
    pool_size = 2
    num_queries = 10
    
    print(f"\nExecuting {num_queries} queries with pool_size={pool_size}")
    print("This will force connection reuse.\n")
    
    with ConnectionPool(config, pool_size=pool_size) as pool:
        initial_stats = pool.get_stats()
        print(f"Initial pool stats: {initial_stats}")
        
        # Execute queries
        with ThreadPoolExecutor(max_workers=pool_size) as thread_pool:
            futures = [
                thread_pool.submit(
                    executor.execute_with_pool,
                    f"SELECT {i} AS value",
                    pool,
                    True
                )
                for i in range(1, num_queries + 1)
            ]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        final_stats = pool.get_stats()
        print(f"\nFinal pool stats: {final_stats}")
        print(f"\nAnalysis:")
        print(f"  Created connections: {final_stats['created_connections']}")
        print(f"  Total acquisitions: {final_stats['total_acquired']}")
        print(f"  Reuse factor: {final_stats['total_acquired'] / final_stats['created_connections']:.1f}x")
    
    print(f"{'='*60}\n")


def example_pool_with_custom_config():
    """Example using pool with custom connection configuration."""
    print("=" * 60)
    print("Example 4: Pool with Custom Configuration")
    print("=" * 60)
    
    # Custom configuration
    config = ConnectionConfig(
        host="localhost",
        port=8080,
        user="admin",
        catalog="memory",
        schema="default",
        http_scheme="http"
    )
    
    print(f"\nCustom config: {config}")
    
    executor = QueryExecutor(connection=config)
    
    with ConnectionPool(config, pool_size=3, timeout=10.0) as pool:
        print(f"Pool timeout: {pool.timeout}s")
        print(f"Pool size: {pool.pool_size}")
        
        # Execute a few queries
        queries = ["SELECT 1", "SELECT 2", "SELECT 3"]
        
        with ThreadPoolExecutor(max_workers=3) as thread_pool:
            futures = [
                thread_pool.submit(executor.execute_with_pool, q, pool)
                for q in queries
            ]
            
            results = [f.result() for f in as_completed(futures)]
        
        print(f"\nExecuted {len(results)} queries successfully")
        print(f"Pool stats: {pool.get_stats()}")
    
    print(f"{'='*60}\n")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Connection Pooling Examples for Concurrent Query Execution")
    print("=" * 60 + "\n")
    
    try:
        # Run examples
        example_sequential_execution()
        example_concurrent_execution_with_pool()
        example_pool_reuse()
        example_pool_with_custom_config()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
