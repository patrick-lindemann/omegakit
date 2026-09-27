from pathlib import Path

import pytest
from omegaconf import OmegaConf

from omegakit import load_config
from omegakit.resolvers.paths import register_paths_resolver


def test_load_resolves_paths(tmp_path: Path, write_yaml):
    register_paths_resolver({"root_dir": tmp_path})
    cfg = load_config(write_yaml("c.yaml", "p: ${paths:root_dir}\n"))
    assert cfg.p == str(tmp_path)


def test_paths_snapshot_and_unknown_key(tmp_path):
    paths = {"data": tmp_path}
    register_paths_resolver(paths)
    paths["data"] = "changed"
    cfg = OmegaConf.create({"path": "${paths:data}", "unknown": "${paths:missing}"})
    assert cfg.path == str(tmp_path)
    assert cfg.unknown is None


def test_paths_replacement_is_explicit():
    register_paths_resolver({"data": "old"})
    with pytest.raises(ValueError, match="already registered"):
        register_paths_resolver({"data": "new"})
    register_paths_resolver({"data": "new"}, replace=True)
    assert OmegaConf.create({"path": "${paths:data}"}).path == "new"
