# Research Questions for TriBench Dissertation

**Document Version:** 1.0  
**Date:** January 20, 2026  
**Status:** Proposed - Pending Validation

---

## Executive Summary

This document defines the research questions for evaluating the TriBench benchmarking framework. The questions are organized into three categories that collectively validate the framework, demonstrate its utility, and differentiate it from alternatives.

**Distribution:**
- 30% Framework Validation (proves the tool works correctly)
- 40% Scientific Demonstration (uses the tool to discover new knowledge)
- 30% Capability Differentiation (shows unique features)

---

## RQ1: Framework Reproducibility and Overhead

### Research Question

**"Does TriBench produce reproducible results across repeated executions, different infrastructure deployments, and varying configurations with acceptable framework overhead?"**

### Category
Framework Validation (Core Technical Requirements)

### Motivation

**Benchmarking Framework Requirements:**
A reliable benchmarking framework must satisfy four fundamental properties:
1. **Reproducibility:** Same experiment → same results (within statistical bounds)
2. **Portability:** Works consistently across different infrastructure (local, cloud, hybrid)
3. **Low Overhead:** Framework measurement overhead doesn't distort actual performance
4. **Configuration Stability:** Different experiment configurations don't affect result quality

**TriBench's Claims:**
- Automated lifecycle management ensures clean state between runs → reproducible results
- Containerization provides infrastructure abstraction → portable across Docker/Kubernetes
- Lightweight monitoring architecture → minimal measurement intrusion
- YAML-based configuration → consistent experiment definitions

**Why This Matters:**
- **Reproducibility** validates that results are trustworthy, not measurement artifacts
- **Portability** proves framework works in development (local) and production (cloud)
### Hypothesis

**H1a: Reproducibility (Repeated Executions)**
```
Multiple runs of the same experiment should produce statistically equivalent results

Expected: CV (Coefficient of Variation) ≤ 10% across 10 repeated runs
Measures: Execution time, memory usage, CPU time consistency
```

**H1b: Portability (Infrastructure Independence)**
```
Same experiment on different infrastructure should show equivalent performance patterns

Expected: Mean execution time difference ≤ 20% (accounting for hardware differences)
### Experiment Design

#### Test Matrix

This experiment uses a **3×3×2 factorial design**:
- **3 Infrastructures:** Local Docker, Kind (local K8s), GKE (cloud K8s)
- **3 Query Patterns:** Simple (Q1, Q6), Medium (Q3, Q12), Complex (Q9, Q18)
- **2 Benchmark Suites:** TPC-H SF1, TPC-DS SF1 (to test different workload characteristics)

#### Dimension 1: Reproducibility Test

**Objective:** Measure result consistency across repeated executions

**Configuration:**
```yaml
# experiments/reproducibility-test.yaml
name: "reproducibility-validation"
description: "Test result consistency across 10 runs"

runs: 10  # Repeated executions
warmup_runs: 0  # No warmup - test cold start consistency

connection:
  host: "localhost"
  port: 8080
  catalog: "iceberg"
  schema: "tpch"

query_files:
  - "apps/tpch/queries/q01.sql"  # Simple scan
  - "apps/tpch/queries/q03.sql"  # Medium join
  - "apps/tpch/queries/q09.sql"  # Complex join

validation:
  min_success_rate: 1.0
```

**Execution:**
```bash
# Run 10 independent experiment executions (not just 10 runs within one execution)
for trial in {1..10}; do
  tribench exp run reproducibility-test.yaml --name "trial_${trial}"
done

# Analyze variance across trials
tribench res analyze reproducibility \
  --experiments trial_1 trial_2 ... trial_10 \
  --metric execution_time_ms \
  --output reproducibility_report.csv
```

**Metrics:**
- **Coefficient of Variation (CV)** per query across 10 trials
- **95% Confidence Interval** for mean execution time
- **Mann-Whitney U Test** between trial pairs (check for systematic drift)

#### Dimension 2: Infrastructure Portability Test

**Objective:** Validate consistent behavior across deployment environments

**Infrastructure Configurations:**

**A. Local Docker (Baseline)**
```yaml
# config/hosts/docker.conf
backend = "docker"
docker {
  compose_file = "systems/trino/docker-compose.yml"
  network = "tribench-net"
}
### Metrics

#### Primary Metrics

**1. Reproducibility Score**
```
Coefficient of Variation (CV) per query:
CV = (Standard Deviation / Mean) × 100%

Target: CV ≤ 10% for repeated executions
Interpretation: Lower CV = more reproducible results
```

**2. Infrastructure Portability Index**
```
Normalized Execution Time Ratio:
Ratio = ExecutionTime_Target / ExecutionTime_Baseline

Example:
Docker (baseline): 45.2s
Kind: 46.8s → Ratio = 1.035 (+3.5% overhead)
GKE: 52.1s → Ratio = 1.153 (+15.3% overhead, acceptable for cloud)

Target: Ratio ∈ [0.8, 1.5] (within 50% range)
```

**3. Framework Overhead Percentage**
```
Overhead = (ExecutionTime_Framework - ExecutionTime_Baseline) / ExecutionTime_Baseline × 100%

Components:
- Orchestration overhead (lifecycle management)
- Monitoring overhead (metric collection)
- Storage overhead (result writing)

Target: Total overhead ≤ 5%
```

**4. Configuration Stability Score**
```
Variance across configurations:
Stability = 1 - (max(CV_configs) - min(CV_configs)) / mean(CV_configs)

Target: Stability ≥ 0.80 (CVs differ by ≤20%)
Interpretation: High stability = config changes don't affect result quality
```

#### Secondary Metrics

**5. Statistical Equivalence Tests**
```
Welch's t-test for comparing repeated executions:
H₀: μ_trial1 = μ_trial2 (no systematic difference)
Accept H₀ if p > 0.05 (95% confidence)
### Success Criteria

**Framework Validates IF:**

1. **Reproducibility (H1a):**
   - ≥80% of queries show CV ≤ 10% across repeated runs
   - ≥90% of trial pairs are statistically equivalent (p > 0.05)
   - No systematic drift detected (regression slope ≈ 0)

2. **Portability (H1b):**
   - Local infrastructures (Docker, Kind) show <10% execution time difference
   - Cloud (GKE) shows 10-30% overhead (acceptable for network/shared hardware)
   - Query ranking correlation ρ ≥ 0.85 across all infrastructures

3. **Framework Overhead (H1c):**
   - Total overhead ≤ 5% of execution time
   - Orchestration overhead ≤ 2%
   - Monitoring overhead ≤ 3%

4. **Configuration Stability (H1d):**
   - Configuration variations show <15% CV difference for same query
   - Stability score ≥ 0.80 across all config permutations

5. **Cross-Benchmark Consistency:**
   - TPC-H and TPC-DS both show CV ≤ 10%
   - Framework maintains reproducibility across different workload patterns

5. **Monitoring-Overhead**
 - Run experiment with monitoring and without
 - Compare

**Framework Fails IF:**
- Reproducibility: >30% of queries show CV >15% (high variance)
- Portability: Local infrastructures differ by >20% (container abstraction broken)
- Overhead: Total overhead >10% (framework cost dominates)
- Stability: Config changes cause >50% CV variation (framework is brittle)
- Failure handling: Recovery rate <90% (leaves broken state)

### Expected Contribution

**If Hypothesis Confirmed:**
> "This experiment would validate that TriBench meets the fundamental requirements of a scientific benchmarking framework: reproducible results (CV ≤ 10%), infrastructure portability (consistent behavior across Docker/Kubernetes), minimal measurement intrusion (≤5% overhead), and configuration stability. These properties establish TriBench as a reliable tool for performance research, enabling subsequent experiments (RQ2, RQ3) with confidence in measurement accuracy."

**Potential Outcomes:**

**Scenario A: Full Validation (Best Case)**
- All metrics meet targets → Framework is production-ready
- Reproducibility + low overhead → Trustworthy measurements
- Portability proven → Useful for both development (local) and research (cloud)

**Scenario B: Partial Validation (Common Case)**
- Most metrics meet targets, some edge cases fail
- Example: High CV on complex queries (Q18, Q9) → Document limitations
- Example: GKE shows 40% overhead → Acceptable, but document cloud cost

**Scenario C: Overhead Issues (Risk)**
- Framework overhead >10% → Need optimization
- Monitoring is too intrusive → Provide "lightweight mode"
- Result: Framework works but with documented performance cost

**Scenario D: Reproducibility Failure (Critical)**
- CV >15% consistently → Deep investigation required
- Possible causes: Container not providing true isolation, external system interference
- Result: Requires architectural changes before proceeding with other RQs

**Value Regardless of Outcome:**
- Even negative results provide value: "We quantified the reproducibility limits of containerized benchmarking"
- Overhead quantification informs practitioners: "Expect 5% measurement cost for this fidelity"
- Infrastructure comparison guides deployment decisions
- CPU time (vs. cgroup metrics)

Target: Accuracy ≥ 95% for all metrics
```

**8. Failure Recovery Rate**
```
Inject failures (OOM, timeout, network partition)
Measure framework's ability to handle gracefully

Recovery_Rate = Successful_Cleanups / Total_Failures

Target: Recovery_Rate ≥ 95% (framework doesn't leave broken state)
```ocker (local): Fastest absolute time (no network overhead)
- Kind (local): Similar to Docker (same hardware, K8s overhead minimal)
- GKE (cloud): Slower absolute time (network latency, shared hardware), but same relative performance ranking

#### Dimension 3: Framework Overhead Test

**Objective:** Quantify TriBench's measurement intrusion

**Baseline (No Framework):**
```bash
# Manual execution without TriBench
docker-compose -f systems/trino/docker-compose.yml up -d
time trino --server localhost:8080 \
  --catalog iceberg \
  --schema tpch \
  --file apps/tpch/queries/q09.sql
docker-compose -f systems/trino/docker-compose.yml down
```

**TriBench (With Monitoring):**
```bash
# With full monitoring enabled
tribench exp run q09-overhead-test.yaml \
  --monitoring-enabled \
  --name "with_monitoring"
```

**TriBench (Monitoring Disabled):**
```bash
# Minimal overhead (only orchestration)
tribench exp run q09-overhead-test.yaml \
  --monitoring-disabled \
  --name "without_monitoring"
```

**Metrics:**
```python
# Calculate overhead
overhead_orchestration = (without_monitoring - baseline) / baseline
overhead_monitoring = (with_monitoring - without_monitoring) / without_monitoring
overhead_total = (with_monitoring - baseline) / baseline

print(f"Orchestration overhead: {overhead_orchestration:.2%}")
print(f"Monitoring overhead: {overhead_monitoring:.2%}")
print(f"Total framework overhead: {overhead_total:.2%}")
```

**Expected Results:**
- Orchestration overhead: 1-2% (lifecycle management, result storage)
- Monitoring overhead: 2-3% (JMX polling, K8s metrics collection)
- Total overhead: 3-5% (acceptable for benchmarking)

#### Dimension 4: Configuration Stability Test

**Objective:** Ensure different experiment configurations don't affect result quality

**Configuration Variations:**
```yaml
# Base configuration
runs: 10
warmup_runs: 2
timeout_seconds: 600
validation: { min_success_rate: 1.0 }

# Variation 1: More runs
runs: 20
warmup_runs: 2

# Variation 2: No warmup
runs: 10
warmup_runs: 0

# Variation 3: Longer timeout
runs: 10
warmup_runs: 2
timeout_seconds: 1200

# Variation 4: Relaxed validation
runs: 10
warmup_runs: 2
validation: { min_success_rate: 0.9 }
```

**Execution:**
```bash
for config in base more_runs no_warmup long_timeout relaxed; do
  tribench exp run q09-config-test-${config}.yaml \
    --name "config_${config}"
done
```

**Metrics:**
- **CV consistency:** Should all configurations show similar CV for same query?
- **Mean consistency:** Should mean execution time be equivalent (excluding warmup effects)?
- **Outlier detection:** Does increasing runs expose outliers? Does timeout affect variance?

#### Dimension 5: Multi-Benchmark Validation

**Objective:** Test framework consistency across different benchmark workloads

**Benchmark 1: TPC-H (OLAP, analytical queries)**
```bash
tribench exp run tpch-validation.yaml \
  --queries q01,q03,q06,q09,q12,q18 \
  --name "tpch_validation"
```

**Benchmark 2: TPC-DS (Complex multi-stage queries)**
```bash
tribench exp run tpcds-validation.yaml \
  --queries q01,q03,q07,q19,q42,q52 \
  --name "tpcds_validation"
```

**Benchmark 3: Custom Stress Test (Edge cases)**
```yaml
# Custom queries designed to test framework limits
query_files:
  - "stress/long_running.sql"    # 10+ minute query
  - "stress/memory_intensive.sql" # Triggers spilling
  - "stress/highly_parallel.sql"  # 100+ tasks
```

**Metrics:**
- **CV across benchmarks:** Does framework maintain consistency regardless of workload?
- **Failure handling:** Does framework gracefully handle timeouts, OOM, crashes?
- **Resource tracking accuracy:** Does monitoring remain accurate under stress?)
- Memory slowly leaks (small Trino memory leak in catalog connector)
- Connection pool saturates after ~15 runs

#### Scenario B: Stateless Execution (TriBench)
```bash
# Full lifecycle per iteration
for i in {1..20}; do
  tribench exp run query-q9.yaml  # Auto-lifecycle enabled
done
```

**Expected Effects:**
- Each run starts with cold JVM (no JIT optimization)
- Fresh connection to Hive Metastore (no pooling)
- No memory accumulation (container destroyed each time)
- Consistent resource baseline

#### Control Variables
- Same query SQL across all runs
- Same dataset (no data changes between runs)
### Limitations and Threats to Validity

**Internal Validity:**
- **Hardware variation:** Local machines may have background processes affecting measurements
  - Mitigation: Use dedicated hardware, disable unnecessary services, run multiple trials
- **Container overhead variability:** Docker/K8s overhead may vary by OS/version
  - Mitigation: Document exact versions, use consistent container runtime
- **Network conditions:** GKE results affected by internet latency, cloud provider load
  - Mitigation: Run experiments at consistent times, use multiple cloud regions

**External Validity:**
- **System-specific:** Results specific to Trino 434 (other systems may behave differently)
  - Mitigation: Note this is Trino validation; future work could test Spark, Presto
- **Workload-specific:** TPC-H/TPC-DS may not represent all query patterns
  - Mitigation: Include custom stress tests, document query pattern coverage
- **Scale-specific:** SF1 dataset may not reveal issues at larger scales
  - Mitigation: Document as limitation, suggest future work at SF10/SF100

**Construct Validity:**
- **CV measures precision, not accuracy:** Low CV doesn't guarantee correct results
  - Mitigation: Validate result correctness separately (row counts, checksums)
- **Overhead calculation depends on baseline accuracy:** Manual timing may have errors
  - Mitigation: Use multiple measurement methods, report confidence intervals
- **Infrastructure "equivalence" is subjective:** What threshold for different hardware?
  - Mitigation: Document hardware specs, use normalized ratios, statistical tests

**Statistical Validity:**
- **Sample size:** 10 runs may be insufficient for detecting small differences
  - Mitigation: Perform power analysis, increase runs if needed, report effect sizes
- **Multiple comparisons:** Testing many queries increases false positive risk
  - Mitigation: Apply Bonferroni correction, report both corrected and uncorrected p-values
- **Non-normal distributions:** Some metrics (execution time) may be skewed
  - Mitigation: Use non-parametric tests (Mann-Whitney U), log-transform if appropriate

**Confounding Factors:**
- **Time of day effects:** System performance may vary by time (thermal throttling, network)
  - Mitigation: Randomize experiment order, run at consistent times
- **Resource contention:** Multiple experiments running simultaneously
  - Mitigation: Sequential execution, monitor system load, discard contaminated runs

**Mitigation Summary:**
1. Document all environment details (OS, hardware, versions)
2. Use multiple statistical tests (parametric and non-parametric)
3. Report confidence intervals and effect sizes, not just p-values
4. Run pilot studies to validate methodology before full experiments
5. Publicly release all raw data for independent verification
```
Divide 20 runs into 4 windows (runs 1-5, 6-10, 11-15, 16-20)
Calculate CV for each window
Plot CV over time
```

**Expected Pattern:**
- Scenario A: CV increases (contamination accumulates)
- Scenario B: CV flat (no contamination)

**2. Performance Trend Analysis**
```
Linear Regression: ExecutionTime = β₀ + β₁ × RunNumber
```

**Expected Slope (β₁):**
- Scenario A: Positive slope (performance degrades)
- Scenario B: Zero slope (no trend)

**3. Memory Leak Detection**
```
Monitor Container RSS (Resident Set Size) after each run
Plot: Memory_MB = f(RunNumber)
```

**Expected Pattern:**
- Scenario A: Linear growth (memory leak)
- Scenario B: Flat (memory resets each run)

**4. Resource Exhaustion Indicators**
```
- Connection pool size (from Trino JMX)
- GC pause time (from JVM logs)
- Metadata cache hit rate (from Hive Metastore)
```

### Success Criteria

**Framework Validates IF:**
1. Scenario B shows **stable CV** (±2% across all windows)
2. Scenario B shows **flat performance trend** (β₁ ≈ 0, p > 0.05)
3. Scenario A shows **increasing variance** OR **performance drift**
4. Container RSS growth in Scenario A confirms memory leak

**Framework Fails IF:**
- Both scenarios show identical variance patterns (lifecycle has no effect)
- Scenario B shows increasing drift (lifecycle cleanup is incomplete)
- Cold start penalty >50% (lifecycle cost outweighs benefit)

### Expected Contribution

**If Hypothesis Confirmed:**
> "This experiment would demonstrate that TriBench's automated lifecycle management prevents measurement drift, validating the core design decision to enforce stateless execution. The results would quantify the trade-off between cold-start overhead and measurement consistency, providing guidance on when lifecycle isolation is necessary versus when warm execution is acceptable."

**Potential Outcomes:**
- **Strong Validation:** Clear variance reduction and drift elimination → lifecycle is essential
- **Partial Validation:** Modest improvements → lifecycle is beneficial but not critical
- **Null Result:** No measurable difference → reconsider lifecycle necessity or methodology

### Limitations and Threats to Validity

**Internal Validity:**
- Memory leaks may not manifest in 20 runs (need longer runs)
- Cache warming might stabilize after initial runs (not continue indefinitely)
- Cold start variance might decrease with more runs (JVM warmup averaging out)

**External Validity:**
- Results specific to Trino 434 (other systems may behave differently)
- Single query tested (results may not generalize to all TPC-H queries)
- Local execution (cloud environments have different noise characteristics)

**Construct Validity:**
- CV measures spread, not accuracy (could have consistent wrong results)
- Memory leak detection assumes linear growth (might be stepwise)

**Mitigation Strategies:**
1. Run extended tests (100 iterations) to confirm long-term trends
2. Test multiple queries (Q1, Q6, Q9, Q17) to check generalizability
3. Replicate on cloud (GKE) to validate in production-like environment
4. Use statistical tests (Mann-Whitney U) to confirm significance

---

## RQ2: Table Format Performance Tradeoffs

### Research Question

**"What are the quantifiable performance tradeoffs between Apache Iceberg and Hive table formats across metadata-heavy versus scan-heavy query patterns?"**

### Category
Scientific Demonstration (Using TriBench for Discovery)

### Motivation

**Industry Debate:**
- Apache Iceberg promises better metadata management and features (time travel, schema evolution)
- Hive Metastore is the established standard with proven stability
- **Open Question:** What is the actual performance cost of Iceberg's metadata overhead?

**Lack of Empirical Data:**
- Vendor benchmarks are biased (Iceberg creators claim "no overhead")
- Community anecdotes are contradictory ("Iceberg is slower" vs. "Iceberg is faster")
- No controlled study isolating table format effects from infrastructure differences

**Why TriBench Enables This:**
- Identical infrastructure (same Trino version, same hardware, same dataset)
- Automated experiment execution ensures consistency
- Advanced metrics capture planning vs. execution time breakdown

**Why This Matters:**
- Organizations evaluating lakehouse migrations need concrete performance data
- Architects need to know WHEN Iceberg's overhead is acceptable vs. prohibitive
- First empirical study of Iceberg performance at controlled scale

### Hypothesis

**H2a: Planning Time Hypothesis**
```
Iceberg planning time > Hive planning time
Reason: Iceberg reads more metadata files (manifests, snapshots)
Expected magnitude: +20% to +40% slower planning
```

**H2b: Execution Time Hypothesis**
```
Iceberg execution time ≈ Hive execution time (±5%)
Reason: Both use Parquet data files, same scan implementation
Expected magnitude: No significant difference
```

**H2c: Memory Pressure Hypothesis**
```
Iceberg spilled_bytes ≤ Hive spilled_bytes
Reason: Iceberg's better file pruning reduces data scanned
Expected magnitude: -10% to -30% less spilling on selective queries
```

**H2d: Query Pattern Dependency**
```
Metadata-heavy queries: Iceberg planning overhead dominates
Scan-heavy queries: Execution time dominates, formats are equal
Complex queries: Trade-offs balance out
```

### Experiment Design

#### Dataset Preparation

**Scale Factor Selection:**
```
TPC-H Scale Factor 10 (SF10)
Rationale:
- Large enough to stress metadata (lineitem: 60M rows, 1,743 partitions by date)
- Small enough to complete queries in reasonable time (<5 min per query)
- Fits in single-node memory (avoids distributed complexity)
```

**Data Loading:**
```bash
# Generate TPC-H SF10 Parquet files
tribench data generate tpch --scale-factor 10

# Load into Hive format
tribench data load-hive tpch-sf10 \
  --format parquet \
  --partitioned \
  --validate

# Load into Iceberg format (identical data)
tribench data load-iceberg tpch-sf10 \
  --format parquet \
  --partitioned \
  --validate
```

**Validation:**
```bash
# Ensure row counts match
tribench data validate-hive --scale-factor 10
tribench data validate-iceberg --scale-factor 10

# Verify partition counts are identical
SELECT COUNT(DISTINCT l_shipdate) FROM hive.tpch.lineitem;
SELECT COUNT(DISTINCT l_shipdate) FROM iceberg.tpch.lineitem;
# Both should return: 2,526 partitions
```

#### Query Selection (Stratified by Pattern)

**Metadata-Heavy Queries:**
```
Q13: Outer Join with Customer Orders
  - Requires full customer table scan + order lookup
  - Tests join metadata optimization
  
Q15: View Creation (Top Supplier)
  - Involves temporary view creation
  - Tests catalog metadata operations
  
Q22: Counting by Substring Condition
  - Requires scanning all customer records
  - Tests predicate evaluation during planning
```

**Scan-Heavy Queries:**
```
Q1: Aggregate by Line Item Status
  - Full lineitem table scan (60M rows)
  - Minimal metadata, pure computation
  
Q6: Filtered Aggregate
  - Selective scan with predicate pushdown
  - Tests partition pruning effectiveness
  
Q12: Shipping Modes Analysis
  - Large scan with grouping
  - Tests execution engine performance
```

**Complex Queries (Mixed):**
```
Q3: Shipping Priority
  - 3-table join (customer, orders, lineitem)
  - Moderate metadata + moderate scan
  
Q5: Local Supplier Revenue
  - 5-table join with region filtering
  - High join complexity
  
Q9: Product Type Profit
  - 6-table join with aggregation
  - Tests multi-stage execution
```

#### Experiment Execution

**Configuration:**
```yaml
# experiments/iceberg-vs-hive-comparison.yaml
name: "iceberg-vs-hive-performance"
description: "Compare Iceberg and Hive table formats"

runs: 10  # Statistical significance
warmup_runs: 2  # Stabilize JIT
timeout_seconds: 600  # 10 min per query

connection:
  host: "localhost"
  port: 8080
  user: "tribench"
  catalog: "{{ format }}"  # Templated: iceberg or hive
  schema: "tpch"

query_files:
  # Metadata-heavy
  - "apps/tpch/queries/q13.sql"
  - "apps/tpch/queries/q15.sql"
  - "apps/tpch/queries/q22.sql"
  
  # Scan-heavy
  - "apps/tpch/queries/q01.sql"
  - "apps/tpch/queries/q06.sql"
  - "apps/tpch/queries/q12.sql"
  
  # Complex
  - "apps/tpch/queries/q03.sql"
  - "apps/tpch/queries/q05.sql"
  - "apps/tpch/queries/q09.sql"

validation:
  min_success_rate: 1.0  # All queries must succeed
```

**Execution:**
```bash
# Run Hive benchmark
tribench exp run iceberg-vs-hive-comparison.yaml \
  --var format=hive \
  --name "hive-sf10"

# Run Iceberg benchmark
tribench exp run iceberg-vs-hive-comparison.yaml \
  --var format=iceberg \
  --name "iceberg-sf10"
```

### Metrics Collection

**TriBench Captures (from Advanced Metrics Implementation):**

1. **Planning Time** (`planning_time_ms`)
   - Time spent in query compilation and optimization
   - Directly measures metadata overhead

2. **Analysis Time** (`analysis_time_ms`)
   - Semantic analysis of query
   - Includes catalog lookups

3. **Execution Time** (`execution_time_ms`)
   - Actual query processing time
   - Excludes planning and analysis

4. **Total Time**
   ```
   total_time = planning_time + analysis_time + execution_time
   ```

5. **Memory Metrics**
   - `peak_memory_bytes`: Maximum memory used
   - `spilled_bytes`: Disk spill due to memory pressure

6. **Parallelism Metrics**
   - `total_splits`: Parallelism degree
   - `completed_splits`: Successful parallel tasks
   - `total_tasks`: Stage-level parallelism

7. **I/O Metrics** (from query metadata)
   - `input_rows`: Rows read from storage
   - `input_bytes`: Bytes read from storage
   - `output_rows`: Rows returned

8. **File Metrics** (from Iceberg/Hive system tables)
   - File count per table
   - Average file size
   - Partition count

### Analysis Methodology

#### Statistical Tests

**1. Paired t-Test (for each query)**
```
Null Hypothesis (H₀): μ_iceberg = μ_hive (no difference)
Alternative (H₁): μ_iceberg ≠ μ_hive (significant difference)
Significance level: α = 0.05
```

**2. Effect Size (Cohen's d)**
```
d = (mean_iceberg - mean_hive) / pooled_standard_deviation

Interpretation:
- Small effect: |d| = 0.2
- Medium effect: |d| = 0.5
- Large effect: |d| = 0.8
```

**3. Confidence Intervals**
```
95% CI for difference: (iceberg - hive) ± t* × SE
```

#### Performance Metrics

**1. Planning Overhead Ratio**
```
Planning_Overhead = (Iceberg_Planning / Hive_Planning) - 1

Example:
Hive planning: 100ms
Iceberg planning: 130ms
Overhead: +30%
```

**2. Execution Parity Index**
```
Execution_Parity = |Iceberg_Execution - Hive_Execution| / Hive_Execution

Threshold for "equivalent": <5%
```

**3. Total Query Cost**
```
Total_Cost = α × Planning_Time + β × Execution_Time

Where:
α = 1 (planning cost weight)
β = N (number of times query will run in production)

Interpretation:
If query runs once: Planning overhead matters
If query runs 1000x: Execution time dominates
```

**4. Memory Efficiency Ratio**
```
Memory_Efficiency = Hive_Spilled_Bytes / Iceberg_Spilled_Bytes

>1.0 = Iceberg more efficient
<1.0 = Hive more efficient
```

### Analysis Plan

**Planned Visualizations:**

1. **Box Plot: Planning Time by Format**
   - X-axis: Query (Q1, Q6, Q12, ...)
   - Y-axis: Planning time (ms)
   - Two boxes per query: Hive vs. Iceberg

2. **Scatter Plot: Execution Time Correlation**
   - X-axis: Hive execution time (s)
   - Y-axis: Iceberg execution time (s)
   - Diagonal line: y = x (parity)
   - Points near diagonal = equivalent performance

3. **Heatmap: Performance Ratio Matrix**
   - Rows: Queries (Q1, Q6, Q12, ...)
   - Columns: Planning, Execution, Memory
   - Values: Iceberg/Hive ratio

4. **Stacked Bar: Time Breakdown**
   - For each query, show: Planning | Analysis | Execution
   - Compare Hive vs. Iceberg side-by-side

### Expected Contribution

**If Hypothesis Confirmed:**
> "This study would provide the first controlled empirical evaluation of Apache Iceberg's performance characteristics compared to Hive Metastore at scale. Results would quantify the planning overhead while measuring execution parity and memory efficiency, providing practitioners with evidence-based guidance on table format selection."

**Potential Outcomes:**
- **Hypothesis Confirmed:** Planning overhead exists but execution is equivalent → document trade-offs
- **Iceberg Faster:** Planning overhead offset by execution gains → strong recommendation
- **No Difference:** Formats perform identically → choice driven by features, not performance
- **Hive Faster:** Iceberg overhead in both phases → recommend Hive unless features required

### Limitations and Future Work

**Limitations:**
- Single scale factor (SF10) - results may not generalize to SF100 or SF1000
- Single execution environment (local Trino) - distributed clusters may behave differently
- Parquet-only comparison - ORC format not evaluated
- No write performance (INSERT, UPDATE, DELETE) - only read queries

**Threats to Validity:**
- **Internal:** File layout differences (Iceberg might compact differently)
- **External:** Hardware-specific results (SSD vs. HDD, local vs. S3)
- **Construct:** Planning time includes network calls to Metastore (not just table format)

**Future Work:**
1. Scale study to SF100 and SF1000 (cloud object storage required)
2. Evaluate write performance (INSERT/UPDATE/MERGE operations)
3. Test distributed execution (multi-node Trino cluster)
4. Compare v1 vs. v2 Iceberg format versions
5. Include ORC and Avro format comparisons

---

## RQ3: Multi-Layer Performance Attribution

### Research Question

**"Can TriBench's dual-layer monitoring (Trino JMX + Kubernetes cgroup metrics) accurately attribute resource consumption to specific query execution stages, enabling actionable performance debugging?"**

### Category
Capability Differentiation (Unique Framework Feature)

### Motivation

**The Performance Debugging Problem:**
- Query is slow, but WHY is it slow?
- Is it CPU-bound, memory-bound, or I/O-bound?
- Which stage is the bottleneck: scan, join, or aggregation?
- Is the overhead in the application (Trino) or infrastructure (K8s, network)?

**Existing Tools Fall Short:**
1. **Trino UI** shows query stages but not infrastructure metrics
2. **Kubernetes Dashboard** shows pod CPU/memory but not which query stage
3. **No correlation** between application performance and infrastructure consumption

**TriBench's Unique Capability:**
- Collects Trino stage-level metrics (from advanced metrics implementation)
- Collects Kubernetes pod metrics (CPU, memory, network)
- Time-aligns both layers (1-second granularity)
- Provides attribution: "Stage 3 (HashJoin) caused 80% CPU spike"

**Why This Matters:**
- Proves that fine-grained monitoring is not just data collection—it's actionable debugging
- Validates that TriBench's monitoring overhead doesn't obscure the signal
- Demonstrates a workflow practitioners can use in production

### Hypothesis

**H3a: Temporal Correlation**
```
Trino CPU time (from JMX) should strongly correlate with 
Kubernetes container CPU usage (from cgroup metrics)

Expected correlation: ρ ≥ 0.85 (strong positive relationship)
```

**H3b: Stage Attribution Accuracy**
```
Memory pressure events (K8s cgroup pressure stalls) should 
align with Trino stages that report high memory usage

Expected accuracy: ≥90% of memory spikes correctly attributed
```

**H3c: Overhead Quantification**
```
Total container CPU should exceed Trino reported CPU by <5%

The difference represents monitoring overhead + OS overhead
```

### Experiment Design

#### Query Selection

**Target Query: TPC-H Q9 (Product Type Profit)**

**Why Q9:**
- **6-table join** → Distinct execution stages
- **Memory-intensive** → Hash join builds large hash tables
- **CPU-intensive** → Aggregation and sorting
- **I/O-intensive** → Scans multiple large tables (lineitem, orders, part)
- **Predictable stages:**
  1. Table scans (6 parallel)
  2. Hash builds (3 stages)
  3. Probe and join (2 stages)
  4. Aggregation (1 stage)
  5. Sorting (1 stage)

**Query Complexity:**
```sql
-- Q9: Product Type Profit Measure Query
SELECT
    nation,
    o_year,
    SUM(amount) AS sum_profit
FROM
    (
        SELECT
            n_name AS nation,
            EXTRACT(year FROM o_orderdate) AS o_year,
            l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity AS amount
        FROM
            part,
            supplier,
            lineitem,
            partsupp,
            orders,
            nation
        WHERE
            s_suppkey = l_suppkey
            AND ps_suppkey = l_suppkey
            AND ps_partkey = l_partkey
            AND p_partkey = l_partkey
            AND o_orderkey = l_orderkey
            AND s_nationkey = n_nationkey
            AND p_name LIKE '%green%'
    ) AS profit
GROUP BY
    nation,
    o_year
ORDER BY
    nation,
    o_year DESC;
```

**Execution Profile (Expected):**
```
Stage 0: Coordinator (final aggregation)
Stage 1: Sort by nation, o_year
Stage 2: Aggregate SUM(amount)
Stage 3: Join lineitem ⋈ orders
Stage 4: Join partsupp ⋈ supplier
Stage 5: Join part ⋈ nation
Stage 6-11: Table scans (6 tables)
```

#### Infrastructure Setup

**Kubernetes Deployment (GKE):**
```yaml
# Trino Coordinator
resources:
  requests:
    cpu: "2"
    memory: "8Gi"
  limits:
    cpu: "4"
    memory: "8Gi"

# Trino Worker (2 replicas)
resources:
  requests:
    cpu: "2"
    memory: "8Gi"
  limits:
    cpu: "4"
    memory: "8Gi"
```

**Monitoring Configuration:**
```yaml
monitoring:
  enabled: true
  interval_seconds: 1.0  # 1-second granularity
  
  kubernetes:
    enabled: true
    context: "gke_tribench_us-central1-a_tribench-cluster"
    namespace: "tribench"
    label_selector: "app=trino"
    
  trino:
    enabled: true
    stage_metrics: true  # Enable stage-level collection
    jmx_metrics: true    # Enable JMX collection
```

#### Data Collection

**Application Layer (Trino):**

From TriBench's advanced metrics implementation:

1. **Query-Level Metrics** (from `QueryExecution` table)
   - `query_id`: Unique identifier
   - `planning_time_ms`: Query planning
   - `execution_time_ms`: Total execution
   - `cpu_time_ms`: CPU time consumed
   - `peak_memory_bytes`: Maximum memory
   - `spilled_bytes`: Disk spill

2. **Stage-Level Metrics** (from `query_metadata` JSON)
   ```json
   {
     "stages": [
       {
         "stage_id": 0,
         "state": "FINISHED",
         "total_tasks": 1,
         "completed_tasks": 1,
         "cpu_time_ms": 1234,
         "wall_time_ms": 5678,
         "peak_memory_bytes": 524288000,
         "input_rows": 1000000,
         "input_bytes": 250000000
       },
       ...
     ]
   }
   ```

3. **Operator-Level Metrics** (if available)
   - Scan operators: Rows/bytes read
   - Join operators: Hash table size, probe time
   - Aggregate operators: Grouping sets

**Infrastructure Layer (Kubernetes):**

From TriBench's Kubernetes monitoring:

1. **CPU Metrics** (from cgroup)
   ```
   container_cpu_usage_seconds_total
   container_cpu_user_seconds_total
   container_cpu_system_seconds_total
   ```

2. **Memory Metrics** (from cgroup)
   ```
   container_memory_usage_bytes
   container_memory_working_set_bytes
   container_memory_rss
   container_memory_cache
   container_memory_swap
   ```

3. **Memory Pressure Events** (from cgroup v2)
   ```
   memory.pressure (PSI - Pressure Stall Information)
   memory.events.oom_kill
   ```

4. **Network Metrics**
   ```
   container_network_receive_bytes_total
   container_network_transmit_bytes_total
   ```

**Time Synchronization:**
- All metrics timestamped with UNIX epoch milliseconds
- Kubernetes metrics collected every 1 second
- Trino stage metrics reported at stage completion
- Post-processing aligns Trino stage timestamps with K8s metric windows

### Analysis Methodology

#### 1. Temporal Correlation Analysis

**Objective:** Verify that Trino-reported CPU matches container CPU

**Method:**
```python
import pandas as pd
from scipy.stats import pearsonr

# Load time-series data
trino_cpu = pd.read_csv('trino_cpu_time_series.csv')  # 1-second samples
k8s_cpu = pd.read_csv('k8s_cpu_time_series.csv')      # 1-second samples

# Align timestamps (interpolate if necessary)
merged = pd.merge_asof(
    trino_cpu, 
    k8s_cpu, 
    on='timestamp', 
    direction='nearest',
    tolerance=pd.Timedelta('1s')
)

# Calculate correlation
correlation, p_value = pearsonr(
    merged['trino_cpu_ms_per_sec'], 
    merged['k8s_cpu_millicores']
)

print(f"Correlation: ρ = {correlation:.3f}, p = {p_value:.4f}")
```

**Expected Result:**
```
Correlation: ρ = 0.887, p < 0.001
Interpretation: Strong positive correlation, monitoring is accurate
```

**Visualization:**
```python
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(merged['timestamp'], merged['trino_cpu_ms_per_sec'], 
         label='Trino CPU (JMX)', linewidth=2)
plt.plot(merged['timestamp'], merged['k8s_cpu_millicores'] / 1000, 
         label='Container CPU (cgroup)', linewidth=2, alpha=0.7)
plt.xlabel('Time (seconds since query start)')
plt.ylabel('CPU Usage (cores)')
plt.title('Application vs. Infrastructure CPU: Q9 Execution')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('cpu_correlation.png', dpi=300)
```

#### 2. Stage-Level Attribution

**Objective:** Map infrastructure spikes to specific query stages

**Method:**
```python
# Stage boundaries (from Trino metadata)
stages = [
    {"stage_id": 0, "start": 0.0, "end": 45.2, "type": "Coordinator"},
    {"stage_id": 1, "start": 2.1, "end": 44.8, "type": "Sort"},
    {"stage_id": 2, "start": 3.5, "end": 43.2, "type": "Aggregate"},
    {"stage_id": 3, "start": 5.0, "end": 40.1, "type": "HashJoin"},
    # ... more stages
]

# Find peak memory usage period
peak_memory_time = k8s_memory['memory_rss'].idxmax()
peak_memory_value = k8s_memory.loc[peak_memory_time, 'memory_rss']

# Attribute to stage
def find_stage(timestamp, stages):
    for stage in stages:
        if stage['start'] <= timestamp <= stage['end']:
            return stage
    return None

attributed_stage = find_stage(peak_memory_time, stages)
print(f"Peak memory ({peak_memory_value / 1e9:.2f} GB) occurred during:")
print(f"  Stage {attributed_stage['stage_id']}: {attributed_stage['type']}")
```

**Expected Output:**
```
Peak memory (6.83 GB) occurred during:
  Stage 3: HashJoin (lineitem ⋈ orders)
  
Validation: Stage 3 metadata shows:
  - Hash table size: 6.2 GB
  - Input rows: 15,000,000 (orders)
  - Memory spike timing: Matches hash build phase
```

**Accuracy Metric:**
```python
# Define "memory spike" as >20% increase from baseline
spikes = detect_memory_spikes(k8s_memory, threshold=0.20)

# Attribute each spike to a stage
attributions = [find_stage(spike['time'], stages) for spike in spikes]

# Manual validation (ground truth from Trino logs)
correct_attributions = 0
for i, spike in enumerate(spikes):
    manual_stage = validate_against_trino_logs(spike['time'])
    if attributions[i]['stage_id'] == manual_stage:
        correct_attributions += 1

accuracy = correct_attributions / len(spikes)
print(f"Attribution Accuracy: {accuracy:.1%}")
```

**Expected Result:**
```
Attribution Accuracy: 94% (17/18 memory spikes correctly attributed)
```

#### 3. Overhead Quantification

**Objective:** Measure monitoring overhead

**Method:**
```python
# Total CPU consumed (from K8s cgroup)
total_container_cpu = k8s_cpu['cpu_usage_seconds_total'].iloc[-1]

# CPU attributed to Trino (from JMX)
total_trino_cpu = trino_cpu['cumulative_cpu_ms'].iloc[-1] / 1000  # Convert to seconds

# Overhead
overhead_cpu = total_container_cpu - total_trino_cpu
overhead_pct = (overhead_cpu / total_container_cpu) * 100

print(f"Total Container CPU: {total_container_cpu:.2f}s")
print(f"Trino Reported CPU: {total_trino_cpu:.2f}s")
print(f"Overhead: {overhead_cpu:.2f}s ({overhead_pct:.1f}%)")
```

**Expected Result:**
```
Total Container CPU: 185.3s
Trino Reported CPU: 180.1s
Overhead: 5.2s (2.8%)

Breakdown of overhead:
- Kubernetes kubelet: ~1.5s (0.8%)
- Metric collectors: ~2.0s (1.1%)
- OS kernel: ~1.7s (0.9%)
Total: 2.8% (within target <5%)
```

#### 4. Bottleneck Identification Workflow

**Practical Use Case: Query is slow, find the root cause**

**Step 1: Identify slow stage**
```sql
-- Query TriBench results database
SELECT 
    stage_id,
    stage_type,
    wall_time_ms,
    cpu_time_ms,
    peak_memory_bytes,
    input_rows
FROM query_stage_metrics
WHERE query_id = 'q9_run_5'
ORDER BY wall_time_ms DESC
LIMIT 5;
```

**Result:**
```
stage_id | stage_type | wall_time_ms | cpu_time_ms | peak_memory_bytes | input_rows
---------|------------|--------------|-------------|-------------------|------------
3        | HashJoin   | 35200        | 28400       | 7340032000        | 15000000
4        | HashJoin   | 18900        | 15200       | 4200000000        | 8000000
2        | Aggregate  | 8500         | 7800        | 1200000000        | 60000000
```

**Insight:** Stage 3 (HashJoin) is the bottleneck (35.2s out of 45s total)

**Step 2: Check infrastructure metrics during Stage 3**
```python
# Stage 3 time window: 5.0s to 40.1s
stage3_k8s = k8s_metrics[
    (k8s_metrics['timestamp'] >= 5.0) & 
    (k8s_metrics['timestamp'] <= 40.1)
]

# Check resource saturation
print(f"CPU utilization: {stage3_k8s['cpu_pct'].mean():.1f}%")
print(f"Memory utilization: {stage3_k8s['memory_pct'].mean():.1f}%")
print(f"Memory pressure events: {stage3_k8s['memory_pressure'].sum()}")
print(f"Network throughput: {stage3_k8s['network_rx_mbps'].mean():.1f} MB/s")
```

**Result:**
```
CPU utilization: 78% (not saturated, CPUs available)
Memory utilization: 95% (saturated! Memory pressure)
Memory pressure events: 23 (container hitting limit)
Network throughput: 45 MB/s (moderate, not bottleneck)
```

**Diagnosis:**
```
Root Cause: Memory-bound hash join
- Stage 3 builds 7.3 GB hash table (lineitem × orders join)
- Container limit: 8 GB
- Available memory after OS/buffers: ~7.5 GB
- Hash table + metadata exceeds limit → memory pressure
- Pressure causes thrashing, slowing execution

Recommendation:
1. Increase memory limit to 12 GB (50% headroom)
2. OR: Enable spilling to disk (slower but completes)
3. OR: Partition the join (distributed execution)
```

**Step 3: Validate fix**
```bash
# Apply fix: Increase memory limit
tribench exp run q9.yaml --memory 12GB

# Re-run analysis
tribench res queries <run_id> --stage-analysis
```

**Expected Outcome:**
```
Stage 3 execution time: 35.2s → 18.5s (47% improvement)
Memory pressure events: 23 → 0 (eliminated)
Total query time: 45.2s → 28.3s (37% improvement)
```

### Success Criteria

**Framework Validates IF:**

1. ✅ **Temporal Correlation:**
   - Pearson correlation ρ ≥ 0.85
   - p-value < 0.001 (statistically significant)
   - Visual overlay shows aligned spikes

2. ✅ **Attribution Accuracy:**
   - ≥90% of memory spikes correctly attributed to stages
   - ≥85% of CPU spikes correctly attributed to stages
   - Zero false positives (no ghost bottlenecks)

3. ✅ **Overhead Acceptability:**
   - Monitoring overhead <5% of total CPU
   - No >10% query slowdown due to monitoring
   - Metric collection doesn't cause memory pressure

4. ✅ **Actionable Insights:**
   - Can identify bottleneck stage (manual validation)
   - Can recommend fix based on metrics (validated by re-run)
   - Debugging workflow completes in <10 minutes

**Framework Fails IF:**
- Correlation <0.70 (monitoring is inaccurate)
- Attribution accuracy <80% (too many misattributions)
- Overhead >10% (monitoring is too intrusive)
- Cannot identify known bottleneck in test case

### Expected Results

**Quantitative Outcomes:**
```
### Success Criteria

**Framework Validates IF:**

1. **Temporal Correlation:**
   - Pearson correlation ρ ≥ 0.85
   - p-value < 0.001 (statistically significant)
   - Visual overlay shows aligned spikes

2. **Attribution Accuracy:**
   - ≥90% of memory spikes correctly attributed to stages
   - ≥85% of CPU spikes correctly attributed to stages
   - Zero false positives (no ghost bottlenecks)

3. **Overhead Acceptability:**
   - Monitoring overhead <5% of total CPU
   - No >10% query slowdown due to monitoring
   - Metric collection doesn't cause memory pressure

4. **Actionable Insights:**
   - Can identify bottleneck stage (manual validation)
   - Can recommend fix based on metrics (validated by re-run)
   - Debugging workflow completes in <10 minutes

**Framework Fails IF:**
- Correlation <0.70 (monitoring is inaccurate)
- Attribution accuracy <80% (too many misattributions)
- Overhead >10% (monitoring is too intrusive)
- Cannot identify known bottleneck in test case

### Expected Contribution

**If Hypothesis Confirmed:**
> "This experiment would demonstrate that TriBench's dual-layer monitoring architecture achieves high temporal correlation between application-level metrics (Trino JMX) and infrastructure-level metrics (Kubernetes cgroups) with minimal overhead. The framework would enable accurate attribution of resource consumption spikes to specific query execution stages, providing a practical debugging workflow that identifies performance bottlenecks efficiently."

**Potential Outcomes:**
- **Strong Validation:** High correlation (ρ > 0.85) + high attribution accuracy (>90%) → monitoring is production-ready
- **Partial Success:** Good correlation but lower attribution → useful but needs refinement
- **Overhead Issues:** High accuracy but >5% overhead → trade-off between precision and intrusion
- **Null Result:** Poor correlation → fundamental limitation in dual-layer approach

**Practical Impact (if successful):**
- Reduces performance debugging time from hours to minutes
- Eliminates need for manual log parsing and correlation
- Provides evidence-based recommendations (not guesswork)
- Demonstrates monitoring overhead is acceptable for production use

**Chapter 1: Introduction**
- Problem: Benchmarking is hard (variance, configuration complexity, reproducibility)
- Solution: TriBench framework
- Claims: Low overhead, high reproducibility, actionable insights

**Chapter 2: Background**
- Lakehouse architecture (Trino, Iceberg, Kubernetes)
- Existing benchmarking tools (limitations)
- Monitoring architectures (application vs. infrastructure)

**Chapter 3: Design & Implementation**
- TriBench architecture
- Lifecycle management
- Configuration templating
- Dual-layer monitoring

**Chapter 4: Evaluation**
- **RQ1:** Framework validation (proves it works correctly)
- **RQ2:** Scientific discovery (demonstrates utility)
- **RQ3:** Capability demonstration (shows unique value)

**Chapter 5: Discussion**
- Tradeoffs (cold start penalty vs. clean state)
- Guidance (when to use Iceberg, when to use lifecycle isolation)
- Limitations (single-node, specific versions)

**Chapter 6: Related Work**
- Comparison to TPC benchmarks, DBench, Databench
- Position relative to industry practices

**Chapter 7: Conclusion**
- Summary of contributions
- Lessons learned (monitoring overhead matters, metadata costs are real)
- Future work (extend to other systems, distributed execution)

### Why This Works

**1. Validates the Tool (30%)**
- RQ1 proves lifecycle isolation is necessary and effective
- Provides confidence that other results are not measurement artifacts

**2. Demonstrates Utility (40%)**
- RQ2 answers a real industry question with your tool
- Shows TriBench enables research that was previously difficult

**3. Differentiates from Alternatives (30%)**
- RQ3 highlights what makes TriBench unique (multi-layer monitoring)
- Proves the feature is not just "nice to have" but actionable

**4. Tells a Complete Story**
- Not just "I built a tool" (engineering project)
- Not just "I ran benchmarks" (empirical study)
- Instead: "I built a tool that enables new kinds of benchmarking research"

---

## Appendix: Implementation Checklist

### RQ1 Prerequisites
- [ ] Implement `--no-lifecycle` flag in experiment runner
- [ ] Add memory leak detection to monitoring
- [ ] Implement statistical variance analysis in results engine
- [ ] Create automated report generation for CV trends

### RQ2 Prerequisites
- [ ] Load TPC-H SF10 into both Hive and Iceberg formats
- [ ] Validate row counts match exactly
- [ ] Implement YAML variable substitution (format={{format}})
- [ ] Create analysis notebook for statistical tests

### RQ3 Prerequisites
- [ ] Deploy monitoring to GKE (already done)
- [ ] Implement time-series alignment in results database
- [ ] Create correlation analysis scripts
- [ ] Build attribution validation workflow

### Data Collection Scripts
```bash
# RQ1: Variance study
./scripts/rq1_variance_experiment.sh

# RQ2: Iceberg vs. Hive
./scripts/rq2_format_comparison.sh

# RQ3: Multi-layer monitoring
./scripts/rq3_attribution_study.sh
```

### Analysis Notebooks
```
analysis/
├── rq1_variance_analysis.ipynb
├── rq2_format_comparison.ipynb
└── rq3_attribution_validation.ipynb
```

---

**Document Status:** Draft for Review  
**Next Steps:** 
1. Supervisor feedback on RQ scope
2. Pilot study for RQ1 (validate methodology)
3. IRB approval if using human participants (RQ7 alternative)
4. Timeline allocation (6 weeks for all three RQs)

**Questions for Advisor:**
- Is SF10 sufficient or do we need SF100? (compute budget)
- Should we include energy metrics (requires hardware power monitoring)?
- Is 10 runs per configuration enough for statistical power?
- Are three RQs too ambitious for timeline? (Focus on 2?)
