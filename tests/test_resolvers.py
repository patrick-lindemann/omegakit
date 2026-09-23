import subprocess
import sys
from types import ModuleType

import pytest
from omegaconf import OmegaConf

import omegakit.resolvers
from omegakit.resolvers.paths import register_paths_resolver
from omegakit.resolvers.torch import (
    _resolve_dtype,
    register_cuda_available_resolver,
    register_torch_dtype_resolver,
    register_torch_resolvers,
)


def test_import_has_no_side_effects():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
import omegakit
import omegakit.resolvers.torch
from omegaconf import OmegaConf
assert 'torch' not in sys.modules
assert 'dotenv' not in sys.modules
assert 'graspdiff' not in sys.modules
assert not any(OmegaConf.has_resolver(n) for n in ('paths', 'dtype', 'cuda_available'))
""",
        ],
        check=True,
    )


def test_resolvers_package_exports_nothing():
    exports = [
        name
        for name, value in vars(omegakit.resolvers).items()
        if not name.startswith("_") and not isinstance(value, ModuleType)
    ]
    assert exports == []


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


@pytest.mark.parametrize(
    "register",
    [
        register_torch_resolvers,
        register_torch_dtype_resolver,
        register_cuda_available_resolver,
    ],
)
def test_missing_torch_error(monkeypatch, register):
    monkeypatch.setitem(sys.modules, "torch", None)
    with pytest.raises(ImportError, match="Install torch"):
        register()
    assert not OmegaConf.has_resolver("dtype")
    assert not OmegaConf.has_resolver("cuda_available")


def test_real_torch_resolvers():
    torch = pytest.importorskip("torch")
    register_torch_resolvers()
    cfg = OmegaConf.create({"dtype": "${dtype:float32}", "cuda": "${cuda_available:}"})
    assert cfg.dtype is torch.float32
    assert cfg.cuda == torch.cuda.is_available()
    for invalid in ("not_a_dtype", "pi"):
        with pytest.raises(ValueError, match="Invalid torch dtype"):
            _resolve_dtype(invalid)
    with pytest.raises(ValueError, match="already registered"):
        register_torch_resolvers()
    register_torch_resolvers(replace=True)


def test_torch_conflict_does_not_partially_register():
    pytest.importorskip("torch")
    OmegaConf.register_new_resolver("cuda_available", lambda: False)
    with pytest.raises(ValueError, match="already registered"):
        register_torch_resolvers()
    assert not OmegaConf.has_resolver("dtype")
