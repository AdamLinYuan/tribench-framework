"""Tests for bundle manifest loading, path resolution, and lifecycle operations."""

import pytest
import yaml
from pathlib import Path

from tribench.bundle.manifest import (
    Bundle,
    BundleManifest,
    BundleError,
    find_bundle_root,
)


# ---------------------------------------------------------------------------
# BundleManifest.from_dict
# ---------------------------------------------------------------------------

class TestBundleManifestFromDict:
    def test_minimal_valid(self):
        m = BundleManifest.from_dict({"name": "my-bundle"})
        assert m.name == "my-bundle"
        assert m.version == "1.0.0"
        assert m.description == ""
        assert m.paths == {}

    def test_full_fields(self):
        m = BundleManifest.from_dict({
            "name": "full",
            "version": "2.3.0",
            "description": "A full bundle",
            "paths": {"config": "custom_config"},
        })
        assert m.version == "2.3.0"
        assert m.description == "A full bundle"
        assert m.paths == {"config": "custom_config"}

    def test_missing_name_raises(self):
        with pytest.raises(BundleError, match="'name'"):
            BundleManifest.from_dict({"version": "1.0.0"})

    def test_to_dict_roundtrip(self):
        original = {"name": "rt-bundle", "version": "1.2.3"}
        m = BundleManifest.from_dict(original)
        d = m.to_dict()
        assert d["name"] == "rt-bundle"
        assert d["version"] == "1.2.3"

    def test_to_dict_omits_empty_description(self):
        m = BundleManifest.from_dict({"name": "x"})
        assert "description" not in m.to_dict()

    def test_to_dict_omits_empty_paths(self):
        m = BundleManifest.from_dict({"name": "x"})
        assert "paths" not in m.to_dict()


# ---------------------------------------------------------------------------
# Bundle.load
# ---------------------------------------------------------------------------

class TestBundleLoad:
    def test_load_valid(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        assert bundle.name == "test-bundle"
        assert bundle.root == temp_bundle_dir.resolve()

    def test_load_missing_yaml_raises(self, tmp_path):
        with pytest.raises(BundleError, match="No bundle.yaml found"):
            Bundle.load(tmp_path)

    def test_load_invalid_yaml_raises(self, temp_bundle_dir):
        (temp_bundle_dir / "bundle.yaml").write_text("name: test\n  bad-indent: x")
        with pytest.raises(BundleError, match="Failed to parse bundle.yaml"):
            Bundle.load(temp_bundle_dir)

    def test_load_missing_name_raises(self, temp_bundle_dir):
        (temp_bundle_dir / "bundle.yaml").write_text(yaml.dump({"version": "1.0.0"}))
        with pytest.raises(BundleError):
            Bundle.load(temp_bundle_dir)

    def test_load_empty_yaml_uses_defaults(self, temp_bundle_dir):
        """Empty YAML body (null document) gets treated as empty dict — no name → error."""
        (temp_bundle_dir / "bundle.yaml").write_text("")
        with pytest.raises(BundleError):
            Bundle.load(temp_bundle_dir)


# ---------------------------------------------------------------------------
# Bundle path resolution
# ---------------------------------------------------------------------------

class TestBundlePaths:
    def test_default_paths(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        assert bundle.config_path == temp_bundle_dir.resolve() / "config"
        assert bundle.experiments_path == temp_bundle_dir.resolve() / "experiments"
        assert bundle.results_path == temp_bundle_dir.resolve() / "results"
        assert bundle.log_path == temp_bundle_dir.resolve() / "log"
        assert bundle.apps_path == temp_bundle_dir.resolve() / "queries"
        assert bundle.datasets_path == temp_bundle_dir.resolve() / "datasets"

    def test_hosts_path_is_config_hosts(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        assert bundle.hosts_path == bundle.config_path / "hosts"

    def test_application_conf_path(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        assert bundle.application_conf_path == bundle.config_path / "application.conf"

    def test_path_override_in_manifest(self, temp_bundle_dir):
        data = {"name": "test-bundle", "paths": {"config": "custom_conf"}}
        (temp_bundle_dir / "bundle.yaml").write_text(yaml.dump(data))
        bundle = Bundle.load(temp_bundle_dir)
        assert bundle.config_path == temp_bundle_dir.resolve() / "custom_conf"
        # Non-overridden paths still use defaults
        assert bundle.experiments_path == temp_bundle_dir.resolve() / "experiments"

    def test_version_property(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        assert bundle.version == "1.0.0"


# ---------------------------------------------------------------------------
# Bundle.create
# ---------------------------------------------------------------------------

class TestBundleCreate:
    def test_create_scaffolds_directories(self, tmp_path):
        bundle = Bundle.create(tmp_path, name="new-bundle")
        assert (tmp_path / "bundle.yaml").exists()
        assert (tmp_path / "config").is_dir()
        assert (tmp_path / "experiments").is_dir()
        assert (tmp_path / "results").is_dir()
        assert (tmp_path / "log").is_dir()
        assert (tmp_path / "queries").is_dir()

    def test_create_sets_name(self, tmp_path):
        bundle = Bundle.create(tmp_path, name="my-bundle", version="2.0.0")
        assert bundle.name == "my-bundle"
        assert bundle.version == "2.0.0"

    def test_create_already_exists_raises(self, tmp_path):
        Bundle.create(tmp_path, name="first")
        with pytest.raises(BundleError, match="already exists"):
            Bundle.create(tmp_path, name="second")


# ---------------------------------------------------------------------------
# Bundle.validate
# ---------------------------------------------------------------------------

class TestBundleValidate:
    def test_validate_complete_bundle_no_issues(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        issues = bundle.validate()
        assert issues == []

    def test_validate_reports_missing_dirs(self, tmp_path):
        # Only write bundle.yaml, no subdirs
        (tmp_path / "bundle.yaml").write_text(yaml.dump({"name": "bare"}))
        bundle = Bundle.load(tmp_path)
        issues = bundle.validate()
        assert len(issues) > 0
        assert any("experiments" in i or "config" in i or "results" in i for i in issues)


# ---------------------------------------------------------------------------
# Bundle.list_experiments
# ---------------------------------------------------------------------------

class TestBundleListExperiments:
    def test_returns_yaml_files(self, temp_bundle_dir):
        exp_dir = temp_bundle_dir / "experiments"
        (exp_dir / "exp1.yaml").write_text("name: exp1\nsystem: trino")
        (exp_dir / "exp2.yaml").write_text("name: exp2\nsystem: trino")
        bundle = Bundle.load(temp_bundle_dir)
        exps = bundle.list_experiments()
        names = {p.name for p in exps}
        assert "exp1.yaml" in names
        assert "exp2.yaml" in names

    def test_returns_empty_when_no_yamls(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        assert bundle.list_experiments() == []

    def test_returns_empty_when_experiments_dir_missing(self, tmp_path):
        (tmp_path / "bundle.yaml").write_text(yaml.dump({"name": "x"}))
        bundle = Bundle.load(tmp_path)
        assert bundle.list_experiments() == []


# ---------------------------------------------------------------------------
# Bundle.summary / __repr__
# ---------------------------------------------------------------------------

class TestBundleRepresentation:
    def test_repr_contains_name(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        assert "test-bundle" in repr(bundle)

    def test_summary_contains_name_and_paths(self, temp_bundle_dir):
        bundle = Bundle.load(temp_bundle_dir)
        s = bundle.summary()
        assert "test-bundle" in s
        assert "Experiments" in s


# ---------------------------------------------------------------------------
# find_bundle_root
# ---------------------------------------------------------------------------

class TestFindBundleRoot:
    def test_finds_bundle_in_current_dir(self, temp_bundle_dir):
        result = find_bundle_root(start=temp_bundle_dir)
        assert result == temp_bundle_dir.resolve()

    def test_finds_bundle_in_ancestor(self, temp_bundle_dir):
        nested = temp_bundle_dir / "a" / "b" / "c"
        nested.mkdir(parents=True)
        result = find_bundle_root(start=nested)
        assert result == temp_bundle_dir.resolve()

    def test_returns_none_when_not_found(self, tmp_path):
        # tmp_path has no bundle.yaml and its parents should not either
        result = find_bundle_root(start=tmp_path / "no_bundle_here")
        assert result is None
