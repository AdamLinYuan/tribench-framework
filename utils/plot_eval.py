#!/usr/bin/env python3
"""
plot_eval.py — Generate all 7 dissertation evaluation figures.

Usage:
    python utils/plot_eval.py [--output figures/]

Figures:
    7.1  Bar chart    — TPC-H 22-query wall-clock times (Docker, SF1)
    7.2  Time-series  — CPU % + memory during Docker experiment
    7.3  Bar chart    — TPC-DS query latencies on GPG (mean ± std dev)
    7.4  Stacked area — Per-pod CPU over time during Q9 (GPG)
    7.5  Line chart   — TPC-H query latency vs workers (GKE 1w/2w/4w)
    7.6  Gantt        — Suite execution timeline (GKE 4w)
    7.7  Grouped bar  — Monitoring overhead % (on vs off, 3 environments)
"""

import argparse
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# Paths & experiment IDs  (update these if your IDs differ)
# ---------------------------------------------------------------------------

BASE    = Path(__file__).parent.parent
BUNDLES = BASE / "bundles"

DB = {
    "docker": BUNDLES / "docker"  / "results" / "tribench.db",
    "gpg":    BUNDLES / "gpg"     / "results" / "tribench.db",
    "gcp-1w": BUNDLES / "gcp-1w"  / "results" / "tribench.db",
    "gcp-2w": BUNDLES / "gcp-2w"  / "results" / "tribench.db",
    "gcp-4w": BUNDLES / "gcp-4w"  / "results" / "tribench.db",
}

# Map logical names → experiment IDs as shown by `tribench res list`
EXP = {
    "docker": {
        "tpch_main":    4,   # tpch-all-2  (SF1, 3 runs)
        "overhead_on":  11,  # overhead-on4  (SF1, 30 runs)
        "overhead_off": 12,  # overhead-off5 (SF1, 30 runs)
    },
    "gpg": {
        "tpcds":        3,   # tpcds-gpg   (SF10, 5 runs)
        "pod_metrics":  7,   # pod-metrics (Q9, SF1)
        "overhead_on":  1,
        "overhead_off": 2,
        "portability":  6,
    },
    "gcp-1w": {
        "portability":  3,
        "overhead_on":  1,
        "overhead_off": 2,
    },
    "gcp-2w": {
        "portability":  4,
        "overhead_on":  5,
        "overhead_off": 6,
    },
    "gcp-4w": {
        "portability":   4,
        "overhead_on":   3,
        "overhead_off":  2,
        "tpcds":         6,
        "custom":        7,
        "tpch_sf_tiny":  8,
        "tpch_sf1":      9,
        "tpch_sf10":     10,
        "tpch_sf100":    11,
    },
}

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

C = {
    "blue":   "#2563EB",
    "orange": "#EA580C",
    "green":  "#16A34A",
    "red":    "#DC2626",
    "purple": "#7C3AED",
    "grey":   "#9CA3AF",
    "teal":   "#0891B2",
}

ENV_COLORS = {
    "Docker":   C["blue"],
    "GPG K8s":  C["purple"],
    "GKE 4w":   C["orange"],
}


def set_style() -> None:
    plt.rcParams.update({
        "font.family":        "serif",
        "font.size":          10,
        "axes.titlesize":     11,
        "axes.labelsize":     10,
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        "legend.fontsize":    9,
        "figure.dpi":         150,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.grid":          True,
        "grid.alpha":         0.3,
        "grid.linestyle":     "--",
        "grid.color":         "#D1D5DB",
    })

# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

def _conn(bundle: str) -> sqlite3.Connection:
    path = DB[bundle]
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {path}")
    return sqlite3.connect(path)


def _ts(value) -> float:
    """Convert a stored timestamp (ISO string or float) to a Unix float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # ISO string: "2026-03-15 19:32:45.123456"
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def measured_run_ids(bundle: str, exp_id: int) -> list[int]:
    c = _conn(bundle)
    rows = c.execute(
        "SELECT id FROM experiment_runs WHERE experiment_id=? AND run_type='measured' ORDER BY run_number",
        (exp_id,)
    ).fetchall()
    c.close()
    return [r[0] for r in rows]


def query_raw(bundle: str, exp_id: int) -> dict[str, list[float]]:
    """Return {query_name: [exec_time_s, ...]} for all measured runs."""
    run_ids = measured_run_ids(bundle, exp_id)
    if not run_ids:
        return {}
    c = _conn(bundle)
    placeholders = ",".join("?" * len(run_ids))
    rows = c.execute(
        f"SELECT query_name, execution_time FROM query_executions "
        f"WHERE run_id IN ({placeholders}) AND status='completed' ORDER BY query_name",
        run_ids
    ).fetchall()
    c.close()
    result: dict[str, list[float]] = {}
    for name, t in rows:
        result.setdefault(name, []).append(t)
    return result


def query_stats(bundle: str, exp_id: int) -> list[tuple[str, float, float]]:
    """Return [(query_name, mean_s, std_s), ...] sorted by query name."""
    raw = query_raw(bundle, exp_id)
    out = []
    for name, times in raw.items():
        arr = np.array(times)
        out.append((name, float(arr.mean()), float(arr.std())))
    return out


def monitoring_series(bundle: str, exp_id: int, metric_name: str) -> tuple[list, list]:
    """Return (timestamps_rel_s, values) from the first measured run."""
    run_ids = measured_run_ids(bundle, exp_id)
    if not run_ids:
        return [], []
    c = _conn(bundle)
    rows = c.execute(
        "SELECT timestamp, value FROM monitoring_metrics "
        "WHERE run_id=? AND metric_name=? ORDER BY timestamp",
        (run_ids[0], metric_name)
    ).fetchall()
    c.close()
    if not rows:
        return [], []
    ts = [_ts(r[0]) for r in rows]
    vs = [r[1] for r in rows]
    t0 = ts[0]
    return [t - t0 for t in ts], vs


def query_start_offsets(bundle: str, exp_id: int) -> list[float]:
    """Return list of query start times (seconds from run start) for first measured run."""
    run_ids = measured_run_ids(bundle, exp_id)
    if not run_ids:
        return []
    c = _conn(bundle)
    run_start = c.execute(
        "SELECT start_time FROM experiment_runs WHERE id=?", (run_ids[0],)
    ).fetchone()
    rows = c.execute(
        "SELECT start_time FROM query_executions WHERE run_id=? AND status='completed' ORDER BY start_time",
        (run_ids[0],)
    ).fetchall()
    c.close()
    if not run_start or not rows:
        return []
    t0 = _ts(run_start[0])
    return [_ts(r[0]) - t0 for r in rows]


def pod_cpu_series(bundle: str, exp_id: int) -> dict[str, tuple[list, list]]:
    """Return {pod_label: (timestamps_rel_s, cpu_values)} from kubernetes pod metrics."""
    run_ids = measured_run_ids(bundle, exp_id)
    if not run_ids:
        return {}
    c = _conn(bundle)
    rows = c.execute(
        "SELECT timestamp, value, labels FROM monitoring_metrics "
        "WHERE run_id=? AND metric_type='kubernetes_pod' AND metric_name LIKE '%cpu%' "
        "ORDER BY timestamp",
        (run_ids[0],)
    ).fetchall()
    c.close()
    pods: dict[str, tuple[list, list]] = {}
    for ts_raw, val, labels_json in rows:
        try:
            pod = json.loads(labels_json or "{}").get("pod", "unknown")
        except (json.JSONDecodeError, TypeError):
            pod = "unknown"
        ts_list, v_list = pods.setdefault(pod, ([], []))
        ts_list.append(_ts(ts_raw))
        v_list.append(val)
    if not pods:
        return {}
    all_ts = sorted({t for tl, _ in pods.values() for t in tl})
    t0 = all_ts[0]
    return {pod: ([t - t0 for t in tl], vl) for pod, (tl, vl) in pods.items()}


def suite_run_spans(bundle: str, exp_ids: dict[str, int]) -> list[tuple[str, float, float]]:
    """Return [(label, start_s, end_s), ...] relative to earliest start."""
    c = _conn(bundle)
    spans = []
    for label, exp_id in exp_ids.items():
        row = c.execute(
            "SELECT MIN(start_time), MAX(end_time) FROM experiment_runs WHERE experiment_id=?",
            (exp_id,)
        ).fetchone()
        if row and row[0]:
            spans.append((label, _ts(row[0]), _ts(row[1]) if row[1] else _ts(row[0]) + 60))
    c.close()
    if not spans:
        return []
    t0 = min(s[1] for s in spans)
    return [(lbl, s - t0, e - t0) for lbl, s, e in sorted(spans, key=lambda x: x[1])]

# ---------------------------------------------------------------------------
# Query name normalisation
# ---------------------------------------------------------------------------

def short_name(raw: str) -> str:
    """'queries/tpch/q03.sql' or 'tpcds_q03' or 'q3' → 'Q3'"""
    m = re.search(r"(\d+)", raw)
    return f"Q{int(m.group(1))}" if m else raw


def sort_by_number(rows: list) -> list:
    """Sort list whose first element is a query name, by query number."""
    return sorted(rows, key=lambda r: int(re.search(r"(\d+)", r[0]).group(1))
                  if re.search(r"(\d+)", r[0]) else 0)


def save(fig: plt.Figure, out: Path, stem: str) -> None:
    fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(out / f"{stem}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

# ---------------------------------------------------------------------------
# Fig 7.1 — TPC-H 22-query bar chart (Docker, SF1)
# ---------------------------------------------------------------------------

def fig71(out: Path) -> None:
    rows = sort_by_number(query_stats("docker", EXP["docker"]["tpch_main"]))
    if not rows:
        print("Fig 7.1: no data — skipping"); return

    labels = [short_name(r[0]) for r in rows]
    means  = np.array([r[1] for r in rows])
    stds   = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(9, 3.5))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, capsize=3,
           color=C["blue"], alpha=0.85, error_kw={"elinewidth": 1, "ecolor": C["grey"]})
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Execution time (s)")
    ax.set_xlabel("TPC-H query")
    ax.set_title("TPC-H Query Execution Times — Docker, SF1 (3 measured runs, 1 warmup)")
    fig.tight_layout()
    save(fig, out, "fig7_1_tpch_docker")
    print(f"  Fig 7.1 saved  ({len(rows)} queries)")

# ---------------------------------------------------------------------------
# Fig 7.2 — Time-series CPU + memory (Docker TPC-H experiment)
# ---------------------------------------------------------------------------

def _smooth(values: list, window: int = 3) -> np.ndarray:
    """Simple moving average."""
    arr = np.array(values, dtype=float)
    if len(arr) < window:
        return arr
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


def _gsmooth(values: list, sigma: float = 15.0) -> np.ndarray:
    """Gaussian smoothing — better for dense time-series."""
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(np.array(values, dtype=float), sigma=sigma)


def fig72(out: Path) -> None:
    t_cpu, cpu = monitoring_series("docker", EXP["docker"]["tpch_main"], "cpu_percent")
    t_mem, mem = monitoring_series("docker", EXP["docker"]["tpch_main"], "memory_percent")
    q_starts   = query_start_offsets("docker", EXP["docker"]["tpch_main"])

    if not t_cpu:
        print("Fig 7.2: no monitoring data — skipping"); return

    fig, ax = plt.subplots(figsize=(8, 3.2))

    cpu_smooth = _gsmooth(cpu, sigma=15)
    ax.fill_between(t_cpu, cpu_smooth, alpha=0.18, color=C["blue"])
    ax.plot(t_cpu, cpu_smooth, color=C["blue"], lw=1.8, label="CPU %")

    # Show every 4th query boundary with a label
    for i, offset in enumerate(q_starts):
        ax.axvline(x=offset, color=C["grey"], alpha=0.45, lw=0.9, ls=":")
        if i % 4 == 0 and i < len(q_starts):
            ax.text(offset + 0.1, ax.get_ylim()[1] * 0.95 if ax.get_ylim()[1] > 0 else 95,
                    f"Q{i+1}", fontsize=7, color=C["grey"], va="top")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("CPU (%)")
    ax.set_ylim(bottom=0)
    ax.set_title("Host CPU Usage During TPC-H Experiment — Docker, SF1 (22 queries)")

    vline_handle = plt.Line2D([0], [0], color=C["grey"], lw=0.9, ls=":", alpha=0.6)
    ax.legend([ax.lines[0], vline_handle], ["CPU %", "Query boundary"],
              loc="upper right")
    fig.tight_layout()
    save(fig, out, "fig7_2_docker_timeseries")
    print("  Fig 7.2 saved")

# ---------------------------------------------------------------------------
# Fig 7.3 — TPC-DS query latencies on GPG (mean ± std dev)
# ---------------------------------------------------------------------------

def fig73(out: Path) -> None:
    rows = sort_by_number(query_stats("gpg", EXP["gpg"]["tpcds"]))
    if not rows:
        print("Fig 7.3: no data — skipping"); return

    labels = [short_name(r[0]) for r in rows]
    means  = np.array([r[1] for r in rows])
    stds   = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(7, 3.5))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, capsize=4,
           color=C["purple"], alpha=0.85, error_kw={"elinewidth": 1, "ecolor": C["grey"]})
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Execution time (s)")
    ax.set_xlabel("TPC-DS query")
    ax.set_title("TPC-DS Query Latencies — GPG Bare-Metal K8s, SF10, 2 workers (5 runs)")
    fig.tight_layout()
    save(fig, out, "fig7_3_tpcds_gpg")
    print(f"  Fig 7.3 saved  ({len(rows)} queries)")

# ---------------------------------------------------------------------------
# Fig 7.4 — Host CPU + memory during Q9 (GPG, 2 workers)
# Falls back to system_resource metrics when kubernetes_pod is unavailable
# ---------------------------------------------------------------------------

def fig74(out: Path) -> None:
    # Try per-pod first
    pods = pod_cpu_series("gpg", EXP["gpg"]["pod_metrics"])
    if pods:
        pod_names = sorted(pods.keys())
        pod_colors = [C["blue"], C["orange"], C["green"], C["purple"], C["teal"], C["red"]]
        all_ts = sorted({t for pn in pod_names for t in pods[pn][0]})
        if len(all_ts) >= 2:
            series = []
            for pn in pod_names:
                pts, pvs = pods[pn]
                series.append(np.interp(all_ts, pts, pvs) if len(pts) >= 2 else np.zeros(len(all_ts)))
            labels = [pn.split("-")[-1] if "-" in pn else pn for pn in pod_names]
            fig, ax = plt.subplots(figsize=(7, 3.5))
            ax.stackplot(all_ts, series, labels=labels,
                         colors=pod_colors[:len(pod_names)], alpha=0.75)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("CPU (millicores)")
            ax.set_title("Per-Pod CPU During TPC-H Q9 (6-table join) — GPG, 2 workers")
            ax.legend(loc="upper right", ncol=3, title="Pod")
            fig.tight_layout()
            save(fig, out, "fig7_4_pod_cpu")
            print(f"  Fig 7.4 saved  ({len(pod_names)} pods)")
            return

    # Fallback: concatenate all measured runs to show multiple Q9 executions
    exp_id = EXP["gpg"]["pod_metrics"]
    c = _conn("gpg")
    run_ids = [r[0] for r in c.execute(
        "SELECT id FROM experiment_runs WHERE experiment_id=? AND run_type='measured' ORDER BY run_number",
        (exp_id,)).fetchall()]

    # Collect runs that have CPU data; concatenate with a small gap between them
    GAP = 1.0  # seconds gap between runs for visual separation
    all_t, all_cpu = [], []
    cursor = 0.0
    runs_plotted = 0
    run_boundaries = []

    for rid in run_ids:
        rows = c.execute(
            "SELECT timestamp, value FROM monitoring_metrics "
            "WHERE run_id=? AND metric_name='cpu_percent' ORDER BY timestamp", (rid,)
        ).fetchall()
        if not rows:
            continue
        ts = [_ts(r[0]) for r in rows]
        vs = [r[1] for r in rows]
        t0 = ts[0]
        rel = [t - t0 for t in ts]
        if runs_plotted > 0:
            run_boundaries.append(cursor)
        all_t.extend([cursor + r for r in rel])
        all_cpu.extend(vs)
        cursor += rel[-1] + GAP
        runs_plotted += 1
    c.close()

    if not all_t:
        print("Fig 7.4: no monitoring data at all — skipping"); return

    cpu_smooth = _gsmooth(all_cpu, sigma=10)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.fill_between(all_t, cpu_smooth, alpha=0.18, color=C["blue"])
    ax.plot(all_t, cpu_smooth, color=C["blue"], lw=1.8, label="CPU %")

    for i, boundary in enumerate(run_boundaries):
        ax.axvline(x=boundary, color=C["grey"], lw=0.9, ls="--", alpha=0.6)
        ax.text(boundary + 0.05, ax.get_ylim()[1] * 0.95 if ax.get_ylim()[1] > 0 else 95,
                f"Run {i+2}", fontsize=7, color=C["grey"], va="top")
    ax.text(0.05, 0.95, "Run 1", fontsize=7, color=C["grey"],
            transform=ax.transAxes, va="top")

    ax.set_xlabel("Time (s, runs concatenated)")
    ax.set_ylabel("CPU (%)")
    ax.set_ylim(bottom=0)
    ax.set_title("Host CPU During TPC-H Q9 (6-table join) — GPG K8s, 2 workers (repeated runs)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    save(fig, out, "fig7_4_pod_cpu")
    print(f"  Fig 7.4 saved  ({runs_plotted} runs concatenated — K8s Metrics Server not available)")

# ---------------------------------------------------------------------------
# Fig 7.5 — Worker scaling line chart (GKE 1w / 2w / 4w)
# ---------------------------------------------------------------------------

def fig75(out: Path) -> None:
    worker_means: dict[int, list[float]] = {}
    for bundle, w in [("gcp-1w", 1), ("gcp-2w", 2), ("gcp-4w", 4)]:
        rows = query_stats(bundle, EXP[bundle]["portability"])
        worker_means[w] = [r[1] for r in rows]

    worker_counts = sorted(worker_means.keys())
    means = [np.mean(worker_means[w]) for w in worker_counts]
    stds  = [np.std(worker_means[w])  for w in worker_counts]

    if not any(means):
        print("Fig 7.5: no portability-anchor data found — skipping"); return

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(worker_counts, means, marker="o", lw=2, color=C["blue"])
    ax.fill_between(worker_counts,
                    [m - s for m, s in zip(means, stds)],
                    [m + s for m, s in zip(means, stds)],
                    color=C["blue"], alpha=0.15, label="±1 std dev")
    for w, m in zip(worker_counts, means):
        ax.annotate(f"{m:.2f}s", (w, m), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)

    ax.set_xticks(worker_counts)
    ax.set_xticklabels([f"{w}w" for w in worker_counts])
    ax.set_xlabel("GKE worker count")
    ax.set_ylabel("Mean execution time (s)")
    ax.set_title("Mean TPC-H Query Latency vs Worker Count — GKE, SF1")
    ax.legend()
    fig.tight_layout()
    save(fig, out, "fig7_5_gke_scaling")
    print(f"  Fig 7.5 saved")

# ---------------------------------------------------------------------------
# Fig 7.6 — Suite execution Gantt (GKE 4w)
# ---------------------------------------------------------------------------

def fig76(out: Path) -> None:
    exp_map = {
        "TPC-DS":         EXP["gcp-4w"]["tpcds"],
        "Custom":         EXP["gcp-4w"]["custom"],
        "TPC-H SF-tiny":  EXP["gcp-4w"]["tpch_sf_tiny"],
        "TPC-H SF1":      EXP["gcp-4w"]["tpch_sf1"],
        "TPC-H SF10":     EXP["gcp-4w"]["tpch_sf10"],
        "TPC-H SF100":    EXP["gcp-4w"]["tpch_sf100"],
    }
    all_spans = suite_run_spans("gcp-4w", exp_map)
    if not all_spans:
        print("Fig 7.6: no run timing data — skipping"); return

    # Compute per-experiment durations in minutes (end - start)
    sf100_row = next((s for s in all_spans if s[0] == "TPC-H SF100"), None)
    rows = [(lbl, (e - s) / 60) for lbl, s, e in all_spans if lbl != "TPC-H SF100"]

    labels   = [r[0] for r in rows]
    durations = [r[1] for r in rows]
    bar_colors = [C["grey"], C["blue"], C["green"], C["orange"], C["purple"]]

    fig, ax = plt.subplots(figsize=(7, 3.2))
    bars = ax.barh(range(len(labels)), durations, height=0.55,
                   color=bar_colors[:len(labels)], alpha=0.87)

    # Labels: inside bar if wide enough, else to the right
    x_max = max(durations) if durations else 1
    for i, dur in enumerate(durations):
        if dur >= x_max * 0.12:
            ax.text(dur / 2, i, f"{dur:.1f} min",
                    ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
        else:
            ax.text(dur + x_max * 0.01, i, f"{dur:.1f} min",
                    ha="left", va="center", fontsize=8.5, color="black")

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Total experiment duration (min)")
    ax.set_title("Suite Experiment Durations — GKE 4-Worker Cluster")
    ax.invert_yaxis()
    ax.set_xlim(left=0, right=x_max * 1.25)
    ax.grid(axis="x", color="0.88", zorder=0)

    # Callout for SF100
    if sf100_row:
        sf100_dur = (sf100_row[2] - sf100_row[1]) / 60
        ax.text(0.98, 0.03,
                f"TPC-H SF100: {sf100_dur:.0f} min (excluded — not to scale)",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=7.5, color=C["red"],
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor=C["red"], alpha=0.9))

    fig.tight_layout()
    save(fig, out, "fig7_6_gantt")
    print(f"  Fig 7.6 saved  ({len(rows)} experiments shown, SF100 as callout)")

# ---------------------------------------------------------------------------
# Fig 7.7 — Monitoring overhead % grouped bar (Docker / GPG / GKE 4w)
# ---------------------------------------------------------------------------

def fig77(out: Path) -> None:
    OVERHEAD_QUERIES = ["Q1", "Q6", "Q18"]

    envs = [
        ("Docker",  "docker", EXP["docker"]["overhead_on"],  EXP["docker"]["overhead_off"]),
        ("GPG K8s", "gpg",    EXP["gpg"]["overhead_on"],     EXP["gpg"]["overhead_off"]),
        ("GKE 4w",  "gcp-4w", EXP["gcp-4w"]["overhead_on"], EXP["gcp-4w"]["overhead_off"]),
    ]

    env_vals:  dict[str, list[float]] = {}
    for label, bundle, on_id, off_id in envs:
        on_map  = {short_name(r[0]): r[1] for r in query_stats(bundle, on_id)}
        off_map = {short_name(r[0]): r[1] for r in query_stats(bundle, off_id)}
        vals = []
        for q in OVERHEAD_QUERIES:
            on_t, off_t = on_map.get(q), off_map.get(q)
            if on_t and off_t and off_t > 0:
                vals.append((on_t - off_t) / off_t * 100)
        env_vals[label] = vals

    all_env_labels = ["Docker", "GPG K8s", "GKE 4w"]
    per_env_means  = [float(np.mean(env_vals[e])) if env_vals[e] else 0.0 for e in all_env_labels]
    per_env_stds   = [float(np.std(env_vals[e]))  if env_vals[e] else 0.0 for e in all_env_labels]
    overall_mean   = float(np.mean(per_env_means))
    overall_std    = float(np.std(per_env_means))

    labels  = all_env_labels + ["Overall Mean"]
    means   = per_env_means  + [overall_mean]
    stds    = per_env_stds   + [overall_std]
    colors  = [ENV_COLORS["Docker"], ENV_COLORS["GPG K8s"], ENV_COLORS["GKE 4w"], C["teal"]]

    fig, ax = plt.subplots(figsize=(6.5, 4.0))

    # Noise floor band (±2%)
    ax.axhspan(-2, 2, color="0.88", alpha=0.55, zorder=1, label="_nolegend_")
    ax.text(1.01, 0, "noise floor", transform=ax.get_yaxis_transform(),
            ha="left", va="center", fontsize=7.5, color="0.55")

    ax.axhline(0, color="black", lw=0.8, zorder=2)
    ax.axhline(5, color=C["red"], ls="--", lw=1.2, label="5% target", zorder=2)

    x = np.arange(len(labels))
    bars = ax.bar(x, means, yerr=stds, capsize=5, color=colors, alpha=0.87, zorder=3,
                  error_kw={"elinewidth": 1.2, "ecolor": C["grey"], "zorder": 4})

    # Value labels — above bar if positive, below if negative
    for xi, (m, s) in enumerate(zip(means, stds)):
        offset = s + 0.15
        va     = "bottom" if m >= 0 else "top"
        ypos   = m + offset if m >= 0 else m - offset
        ax.text(xi, ypos, f"{m:.1f}%", ha="center", va=va,
                fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean overhead (%) across Q1 / Q6 / Q18")
    ax.set_title("Mean Monitoring Overhead — TriBench instrumented vs uninstrumented")
    ax.legend(loc="upper right")
    ax.grid(axis="y", color="0.9", zorder=0)
    fig.tight_layout()
    save(fig, out, "fig7_7_overhead")
    print("  Fig 7.7 saved")

# ---------------------------------------------------------------------------
# Fig 7.8 — TPC-H SF100 query latencies on GKE 4w (mean ± std dev)
# ---------------------------------------------------------------------------

def fig78(out: Path) -> None:
    rows = sort_by_number(query_stats("gcp-4w", EXP["gcp-4w"]["tpch_sf100"]))
    if not rows:
        print("Fig 7.8: no data — skipping"); return

    labels = [short_name(r[0]) for r in rows]
    means  = np.array([r[1] for r in rows])
    stds   = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(10, 3.8))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, capsize=4,
           color=C["orange"], alpha=0.85,
           error_kw={"elinewidth": 1, "ecolor": C["grey"]})
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Execution time (s)")
    ax.set_xlabel("TPC-H query")
    ax.set_title("TPC-H Query Latencies — GKE 4-Worker Cluster, SF100 (3 runs)")
    fig.tight_layout()
    save(fig, out, "fig7_8_tpch_gke_sf100")
    print(f"  Fig 7.8 saved  ({len(rows)} queries)")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dissertation evaluation figures")
    parser.add_argument("--output", default="figures", help="Output directory (default: figures/)")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    set_style()

    print("Generating dissertation figures...")
    fig71(out)
    fig72(out)
    fig73(out)
    fig74(out)
    fig75(out)
    fig76(out)
    fig77(out)
    fig78(out)
    print(f"\nDone. PDFs + PNGs written to: {out.resolve()}/")


if __name__ == "__main__":
    main()
