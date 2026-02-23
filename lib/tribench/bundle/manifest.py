"""
Bundle manifest — loads and validates bundle.yaml.

A bundle.yaml lives at the root of a bundle directory and describes the bundle:

    name: tpch-iceberg
    version: "1.0.0"
    description: "TPC-H benchmark on Iceberg/Trino"
    # paths are all optional — defaults shown below
    paths:
      apps: queries/
      config: config/
      experiments: experiments/
      datasets: datasets/
      log: log/
      results: results/

All path entries are relative to the bundle root (the directory containing
bundle.yaml).  Absolute paths are also accepted.
"""

from __future__ import annotations

import tarfile
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BundleError(Exception):
    """Raised for invalid or missing bundle configurations."""


# ---------------------------------------------------------------------------
# Default sub-directory names
# ---------------------------------------------------------------------------

_DEFAULTS: Dict[str, str] = {
    "apps":        "queries",
    "config":      "config",
    "experiments": "experiments",
    "datasets":    "datasets",
    "log":         "log",
    "results":     "results",
}


# ---------------------------------------------------------------------------
# Manifest dataclass
# ---------------------------------------------------------------------------

@dataclass
class BundleManifest:
    """
    In-memory representation of a bundle.yaml file.

    Attributes:
        name:        Short identifier for the bundle (required).
        version:     Semantic version string (optional).
        description: Human-readable description (optional).
        paths:       Mapping of logical name → relative path override.
    """
    name: str
    version: str = "1.0.0"
    description: str = ""
    paths: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BundleManifest":
        """Parse a dictionary (from YAML) into a BundleManifest."""
        if "name" not in data:
            raise BundleError("bundle.yaml must contain a 'name' field")
        return cls(
            name=data["name"],
            version=str(data.get("version", "1.0.0")),
            description=data.get("description", ""),
            paths=data.get("paths", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary suitable for YAML dumping."""
        d: Dict[str, Any] = {"name": self.name, "version": self.version}
        if self.description:
            d["description"] = self.description
        if self.paths:
            d["paths"] = self.paths
        return d


# ---------------------------------------------------------------------------
# Bundle class
# ---------------------------------------------------------------------------

class Bundle:
    """
    A TriBench bundle — a portable unit for running and sharing experiments.

    Attributes:
        root:      Absolute path to the bundle directory.
        manifest:  Parsed BundleManifest.

    Path properties (resolved relative to root):
        apps_path, config_path, experiments_path, datasets_path,
        log_path, results_path, hosts_path, application_conf_path
    """

    MANIFEST_FILENAME = "bundle.yaml"

    def __init__(self, root: Path, manifest: BundleManifest) -> None:
        self.root = root.resolve()
        self.manifest = manifest

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, bundle_root: Path) -> "Bundle":
        """
        Load a bundle from *bundle_root* (a directory containing bundle.yaml).

        Raises:
            BundleError: If bundle.yaml is missing or invalid.
        """
        bundle_root = Path(bundle_root).resolve()
        manifest_path = bundle_root / cls.MANIFEST_FILENAME

        if not manifest_path.exists():
            raise BundleError(
                f"No bundle.yaml found at: {manifest_path}\n"
                "Run 'tribench bundle create <name>' to create a new bundle."
            )

        try:
            with manifest_path.open() as fh:
                data = yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            raise BundleError(f"Failed to parse bundle.yaml: {exc}") from exc

        manifest = BundleManifest.from_dict(data)
        logger.debug(f"Loaded bundle '{manifest.name}' from {bundle_root}")
        return cls(bundle_root, manifest)

    @classmethod
    def create(cls, bundle_root: Path, name: str,
               version: str = "1.0.0",
               description: str = "") -> "Bundle":
        """
        Scaffold a new bundle directory at *bundle_root*.

        Creates the standard sub-directories and writes bundle.yaml.

        Raises:
            BundleError: If bundle_root already contains a bundle.yaml.
        """
        bundle_root = Path(bundle_root).resolve()
        manifest_path = bundle_root / cls.MANIFEST_FILENAME

        if manifest_path.exists():
            raise BundleError(
                f"A bundle already exists at {bundle_root}.\n"
                "Use 'tribench bundle info' to inspect it."
            )

        manifest = BundleManifest(name=name, version=version, description=description)

        # Create directory structure
        for key, default_dir in _DEFAULTS.items():
            subdir = bundle_root / default_dir
            subdir.mkdir(parents=True, exist_ok=True)
            # Add a .gitkeep so the directory is tracked by git
            (subdir / ".gitkeep").touch()

        # Create config/hosts/ sub-directory
        hosts_dir = bundle_root / "config" / "hosts"
        hosts_dir.mkdir(parents=True, exist_ok=True)
        (hosts_dir / ".gitkeep").touch()

        # Write bundle.yaml
        with manifest_path.open("w") as fh:
            yaml.dump(manifest.to_dict(), fh, default_flow_style=False, sort_keys=False)

        # Write empty application.conf
        app_conf = bundle_root / "config" / "application.conf"
        app_conf.write_text(
            "# Bundle-level configuration overrides.\n"
            "# These are applied on top of reference.conf and before host configs.\n"
            "# See tribench's config/reference.conf for all available settings.\n"
        )

        logger.info(f"Created bundle '{name}' at {bundle_root}")
        return cls(bundle_root, manifest)

    # ------------------------------------------------------------------
    # Resolved path properties
    # ------------------------------------------------------------------

    def _resolve(self, key: str) -> Path:
        """Resolve a logical path key, honouring manifest overrides."""
        rel = self.manifest.paths.get(key, _DEFAULTS[key])
        p = Path(rel)
        return p if p.is_absolute() else (self.root / p)

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def apps_path(self) -> Path:
        return self._resolve("apps")

    @property
    def config_path(self) -> Path:
        return self._resolve("config")

    @property
    def experiments_path(self) -> Path:
        return self._resolve("experiments")

    @property
    def datasets_path(self) -> Path:
        return self._resolve("datasets")

    @property
    def log_path(self) -> Path:
        return self._resolve("log")

    @property
    def results_path(self) -> Path:
        return self._resolve("results")

    @property
    def hosts_path(self) -> Path:
        return self.config_path / "hosts"

    @property
    def application_conf_path(self) -> Path:
        return self.config_path / "application.conf"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        """
        Check bundle structure and return a list of warning/error strings.

        An empty list means the bundle is valid.
        """
        issues: List[str] = []

        required_dirs = {
            "apps":        self.apps_path,
            "config":      self.config_path,
            "experiments": self.experiments_path,
            "log":         self.log_path,
            "results":     self.results_path,
        }

        for label, path in required_dirs.items():
            if not path.exists():
                issues.append(f"Missing directory: {path.relative_to(self.root)} ({label})")

        if not self.hosts_path.exists():
            issues.append(f"Missing directory: config/hosts/")

        return issues

    # ------------------------------------------------------------------
    # Experiment discovery
    # ------------------------------------------------------------------

    def list_experiments(self) -> List[Path]:
        """Return all .yaml files inside the bundle's experiments/ directory."""
        if not self.experiments_path.exists():
            return []
        return sorted(self.experiments_path.rglob("*.yaml"))

    # ------------------------------------------------------------------
    # Archiving
    # ------------------------------------------------------------------

    def archive(self, output_dir: Optional[Path] = None) -> Path:
        """
        Create a compressed tar.gz archive of the bundle's results/ directory.

        The archive is written to *output_dir* (defaults to bundle root) with
        a timestamped filename:
            <bundle-name>-results-<YYYYMMDD-HHMMSS>.tar.gz

        Returns the path to the created archive.
        """
        output_dir = Path(output_dir) if output_dir else self.root
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_name = f"{self.name}-results-{timestamp}.tar.gz"
        archive_path = output_dir / archive_name

        if not self.results_path.exists():
            raise BundleError(
                f"Results directory does not exist: {self.results_path}"
            )

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(self.results_path, arcname="results")

        logger.info(f"Archived results to {archive_path}")
        return archive_path

    # ------------------------------------------------------------------
    # String representations
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Bundle(name={self.name!r}, root={self.root})"

    def summary(self) -> str:
        """Return a human-readable summary string."""
        lines = [
            f"Bundle:      {self.name}",
            f"Version:     {self.version}",
            f"Root:        {self.root}",
        ]
        if self.manifest.description:
            lines.append(f"Description: {self.manifest.description}")
        lines += [
            f"Apps:        {self.apps_path}",
            f"Experiments: {self.experiments_path}",
            f"Datasets:    {self.datasets_path}",
            f"Results:     {self.results_path}",
            f"Log:         {self.log_path}",
            f"Config:      {self.config_path}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bundle root discovery
# ---------------------------------------------------------------------------

def find_bundle_root(start: Optional[Path] = None) -> Optional[Path]:
    """
    Walk up the directory tree from *start* (default: CWD) until a
    directory containing ``bundle.yaml`` is found.

    Returns the bundle root Path, or None if not found.

    Analogous to how ``git`` walks up to find ``.git``.
    """
    path = (Path(start) if start else Path.cwd()).resolve()

    while True:
        if (path / Bundle.MANIFEST_FILENAME).exists():
            return path
        parent = path.parent
        if parent == path:
            break
        path = parent

    return None
