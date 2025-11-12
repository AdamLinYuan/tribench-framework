"""Create sample data in the default database for testing CLI commands."""

from tribench.storage import init_database, ResultStorage
from datetime import datetime

# Initialize default database
init_database()
storage = ResultStorage()

print("Creating sample experiment data...")

# Create experiment
exp_id = storage.create_or_get_experiment(
    name="tpch-q1-test",
    experiment_type="trino_query",
    dataset_name="tpch-sf0.01",
    tags=["test", "tpch"],
)
print(f"✓ Created experiment: tpch-q1-test (ID: {exp_id})")

# Create run
run_id = storage.create_run(
    experiment_id=exp_id,
    run_number=1,
    run_type="measured",
)
print(f"✓ Created run (ID: {run_id})")

# Add query executions
for i in range(3):
    qe_id = storage.add_query_execution(
        run_id=run_id,
        query_name=f"q{i+1}",
        query_sql=f"SELECT COUNT(*) FROM lineitem WHERE l_orderkey < {1000 * (i+1)}",
        execution_time_ms=150.0 * (i + 1),
        status="success",
        start_time=datetime.now(),
        query_id=f"20231112_test_{i:03d}",
    )
    print(f"✓ Added query q{i+1} (ID: {qe_id})")

# Complete run
storage.complete_run(run_id=run_id, status="completed")
print(f"✓ Completed run")

print("\n✅ Sample data created successfully!")
print("\nNow you can test CLI commands:")
print("  tribench res list")
print("  tribench res show 1")
print("  tribench res show tpch-q1-test --runs")
print("  tribench res export 1 --format json")
