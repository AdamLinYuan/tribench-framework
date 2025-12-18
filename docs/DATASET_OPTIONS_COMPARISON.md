# TPC-H Dataset Options: Which One Should You Use?

## The Three Options Explained

### 1. **Trino Built-in TPC-H Connector** (In-Memory, No Storage)
```yaml
connection:
  catalog: "tpch"
  schema: "sf1"  # or sf10, sf100, sf1000, etc.
```

**What it is:**
- Virtual catalog that generates TPC-H data **on-the-fly**
- No actual storage - data generated in memory per query
- Available at any scale factor (sf1, sf10, sf100, etc.)

**Pros:**
- ✅ **No loading required** - instantly available
- ✅ **No storage space** needed
- ✅ **Any scale factor** on demand
- ✅ **Perfect for testing** queries/logic

**Cons:**
- ❌ **Not realistic** - no I/O, no real storage layer
- ❌ **Different performance** - memory generation vs disk reads
- ❌ **No Iceberg features** - can't test table formats, metadata, snapshots
- ❌ **Not benchmarking real systems** - skips storage layer entirely

**Use case:** Quick testing, query validation, development

---

### 2. **Generated Parquet Files** (Local Storage)
```yaml
Location: /Users/adamyuan/.../datasets/tpch-sf1_0/parquet
Format: parquet
Type: generated
```

**What it is:**
- Real Parquet files on your local filesystem
- Generated once using TPC-H `dbgen` tool
- Raw data files, not loaded into Trino yet

**Pros:**
- ✅ **Reusable** - generate once, load multiple times
- ✅ **Portable** - can copy to other systems
- ✅ **Real data files** - actual Parquet format
- ✅ **Source of truth** - can load into different catalogs

**Cons:**
- ❌ **Not queryable yet** - need to load into Trino first
- ❌ **Takes disk space** (306 MB for SF1)
- ❌ **Generation time** (one-time cost)

**Use case:** Intermediate step for loading into real catalogs

---

### 3. **Iceberg Tables** (Loaded in Trino)
```yaml
Location: iceberg.tpch
Format: iceberg
Type: static
```

**What it is:**
- Parquet data loaded into **Apache Iceberg** tables
- Stored in S3/MinIO with Iceberg metadata
- Real table format with schema evolution, time travel, etc.

**Pros:**
- ✅ **Production-realistic** - mimics real lakehouse architecture
- ✅ **Full Iceberg features** - snapshots, time travel, schema evolution
- ✅ **Real I/O patterns** - disk reads, network, caching
- ✅ **Accurate benchmarking** - tests actual data lakehouse performance
- ✅ **Persistent** - survives Trino restarts
- ✅ **Queryable immediately** from Trino

**Cons:**
- ❌ **Requires loading** (takes time to load)
- ❌ **Needs object storage** (MinIO/S3)
- ❌ **More infrastructure** (Hive Metastore, MinIO)

**Use case:** **Real benchmarking, production simulation** ← **USE THIS**

---

## Comparison Table

| Feature | Built-in `tpch` | Parquet Files | Iceberg Tables |
|---------|----------------|---------------|----------------|
| **Query it directly** | ✅ Yes | ❌ No | ✅ Yes |
| **Realistic I/O** | ❌ No (memory) | N/A | ✅ Yes (S3/MinIO) |
| **Storage layer** | ❌ Virtual | ✅ Local disk | ✅ Object store |
| **Table format features** | ❌ None | N/A | ✅ Full Iceberg |
| **Setup time** | 🟢 Instant | 🟡 ~30s generate | 🟡 ~2min load |
| **Disk space** | 🟢 0 MB | 🟡 306 MB | 🔴 600+ MB |
| **Good for benchmarking** | ❌ No | ❌ No | ✅ **YES** |

---

## When to Use Each

### Use **Trino Built-in TPC-H** (`tpch` catalog) when:
- 🧪 Testing query syntax/logic
- 🚀 Quick prototyping
- 📝 Validating queries work
- ⚡ Don't care about I/O performance

**Example:**
```yaml
connection:
  catalog: "tpch"
  schema: "sf1"
```

### Use **Generated Parquet** when:
- 📦 You need source data to load elsewhere
- 🔄 Loading into multiple catalogs (Hive, Iceberg, etc.)
- 💾 Archiving datasets

**NOT for direct querying!**

### Use **Iceberg Tables** (`iceberg.tpch`) when:
- 📊 **Real benchmarking** ← **YOUR CASE**
- 🏗️ Testing production-like architecture
- ⚡ Measuring actual query performance
- 🔍 Testing Iceberg features (snapshots, schema evolution)
- 📈 Comparing storage formats

**Example:**
```yaml
connection:
  catalog: "iceberg"
  schema: "tpch"
```

---

## Your Question: Do You Need to Load Locally?

### Short Answer: **YES, for real benchmarking!**

### Why?

**Built-in `tpch` catalog** is a **test connector**, not a real storage system:

```
Built-in TPC-H:
  Query → Generate in memory → Return
  (No disk I/O, no network, no real storage)

Iceberg Tables:
  Query → Read from MinIO/S3 → Parse Parquet → Cache → Return
  (Real I/O, network latency, compression, columnar reading)
```

**Your benchmark would be meaningless with built-in TPC-H because:**

1. ❌ **No storage layer** - skips 50%+ of query time
2. ❌ **No caching effects** - can't test cache performance
3. ❌ **No network I/O** - no object storage reads
4. ❌ **No table format overhead** - no metadata reads
5. ❌ **Not realistic** - doesn't match production

### Example Performance Difference

Same query, different results:

```bash
# Built-in TPC-H (fake, in-memory)
SELECT COUNT(*) FROM tpch.sf1.lineitem;
→ 0.5 seconds (just generates and counts)

# Iceberg (real, with I/O)
SELECT COUNT(*) FROM iceberg.tpch.lineitem;
→ 3.2 seconds (reads 6M rows from S3, decompresses Parquet)
```

The **3.2s is the real number** you care about!

---

## Recommendation for Your Comparison

### ✅ **Keep using `iceberg.tpch` (SF1 loaded)**

Your current config is **perfect**:

```yaml
connection:
  catalog: "iceberg"    # ✅ Real storage
  schema: "tpch"        # ✅ Loaded SF1 data
```

This tests:
- ✅ Real object storage (MinIO)
- ✅ Real Parquet reading
- ✅ Real Iceberg metadata
- ✅ Real caching behavior
- ✅ **Real connection pooling performance** (your test!)

---

## Quick Command Reference

### Check what's loaded in Trino:

```bash
# List catalogs
trino --execute "SHOW CATALOGS"

# Check built-in TPC-H (always available)
trino --execute "SHOW SCHEMAS FROM tpch"
# → sf1, sf10, sf100, sf1000, etc.

# Check your Iceberg tables
trino --execute "SHOW TABLES FROM iceberg.tpch"
# → nation, region, customer, supplier, part, partsupp, orders, lineitem

# Verify row counts
trino --execute "SELECT COUNT(*) FROM iceberg.tpch.lineitem"
# → Should be 6,001,215 for SF1
```

---

## Summary

**For connection pooling comparison:**

- ❌ DON'T use `tpch.sf1` (built-in) - not realistic
- ✅ DO use `iceberg.tpch` (loaded SF1) - realistic benchmark

**The loading step was necessary** to get real benchmark data!

**The 306MB Parquet files** were the intermediate step to create the Iceberg tables (now in MinIO/S3).

You're currently set up **correctly** for meaningful benchmarking! 🎯
