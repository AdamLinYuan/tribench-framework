"""Integration test for database storage with experiment execution."""

import os
import tempfile
from pathlib import Path
from datetime import datetime


def test_database_storage_integration():
    """Test full workflow: create experiment, run, queries, and retrieve."""
    from tribench.storage import init_database, ResultStorage
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        os.environ['TRIBENCH_DATABASE_URL'] = f"sqlite:///{db_path}"
        
        # Initialize database
        init_database()
        storage = ResultStorage()
        
        print("\n=== Testing Database Storage ===\n")
        
        # 1. Create experiment
        print("1. Creating experiment...")
        exp_id = storage.create_or_get_experiment(
            name="test_tpch_q1",
            experiment_type="trino_query",
            dataset_name="tpch-sf0.01",
            tags=["test", "tpch"],
        )
        print(f"   ✓ Created experiment ID: {exp_id}")
        
        # 2. Create run
        print("\n2. Creating run...")
        run_id = storage.create_run(
            experiment_id=exp_id,
            run_number=1,
            run_type="measured",
        )
        print(f"   ✓ Created run ID: {run_id}")
        
        # 3. Add query executions
        print("\n3. Adding query executions...")
        for i in range(3):
            qe_id = storage.add_query_execution(
                run_id=run_id,
                query_name=f"q{i+1}",
                query_sql=f"SELECT {i+1}",
                execution_time_ms=100.0 * (i + 1),
                status="success",
                start_time=datetime.now(),
                trino_query_id=f"20231115_00000{i}",
            )
            print(f"   ✓ Added query {i+1}, ID: {qe_id}")
        
        # 4. Complete run
        print("\n4. Completing run...")
        storage.complete_run(
            run_id=run_id,
            status="completed",
        )
        print("   ✓ Run completed")
        
        # 5. Retrieve and verify
        print("\n5. Retrieving results...")
        
        # Get experiment
        exp = storage.get_experiment_by_name("test_tpch_q1")
        assert exp is not None
        assert exp["name"] == "test_tpch_q1"
        print(f"   ✓ Retrieved experiment: {exp['name']}")
        
        # Get runs
        runs = storage.get_experiment_runs(exp_id)
        assert len(runs) > 0
        print(f"   ✓ Found {len(runs)} run(s)")
        
        # Get query executions
        query_execs = storage.get_run_query_executions(run_id)
        assert len(query_execs) == 3
        print(f"   ✓ Found {len(query_execs)} query executions")
        
        for qe in query_execs:
            print(f"      - {qe.query_name}: {qe.execution_time_ms}ms ({qe.status})")
        
        # 6. List all experiments
        print("\n6. Listing all experiments...")
        all_experiments = storage.list_experiments()
        assert len(all_experiments) >= 1
        print(f"   ✓ Found {len(all_experiments)} experiment(s) in database")
        
        print("\n=== ✅ All tests passed! ===\n")
        return True


def test_cli_commands():
    """Test CLI result commands."""
    import subprocess
    import json
    
    print("\n=== Testing CLI Commands ===\n")
    
    # First, ensure we have a database with data
    test_database_storage_integration()
    
    # Test list command
    print("1. Testing 'tribench res list'...")
    result = subprocess.run(
        ["python", "-m", "tribench.cli", "res", "list"],
        capture_output=True,
        text=True,
        cwd="/Users/adamyuan/Documents/UofG/Yr 4/Dissertation/Code/tribench-framework"
    )
    
    if result.returncode == 0:
        print("   ✓ List command succeeded")
        print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
    else:
        print(f"   ✗ List command failed: {result.stderr[:200]}")
    
    print("\n=== CLI Test Complete ===\n")


if __name__ == "__main__":
    # Run integration test
    test_database_storage_integration()
    
    # Optionally test CLI
    # test_cli_commands()
