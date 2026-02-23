"""
Bundle management for TriBench.

A bundle is a self-contained, portable directory that packages everything
needed to reproduce a benchmark experiment:

    my-bundle/
    ├── bundle.yaml           # Manifest (name, version, optional path overrides)
    ├── queries/              # Workload query directories (e.g. tpch/, tpcds/)
    ├── config/
    │   ├── application.conf  # Bundle-level HOCON overrides
    │   └── hosts/            # Machine-specific overrides
    ├── datasets/             # Static dataset files
    ├── experiments/          # Experiment YAML definitions
    ├── log/                  # Execution logs
    └── results/              # Experiment run outputs

Usage:
    from tribench.bundle import Bundle, find_bundle_root

    bundle = Bundle.load("/path/to/my-bundle")
    print(bundle.name)          # "my-benchmark"
    print(bundle.experiments_path)  # Path("…/my-bundle/experiments")
"""

from tribench.bundle.manifest import (
    Bundle,
    BundleManifest,
    BundleError,
    find_bundle_root,
    get_active_bundle,
    set_active_bundle,
    clear_active_bundle,
)

__all__ = ["Bundle", "BundleManifest", "BundleError", "find_bundle_root"]
