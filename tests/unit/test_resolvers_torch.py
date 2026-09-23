import sys
from types import ModuleType, SimpleNamespace

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError

from omegakit.resolvers.torch import (
    _resolve_dtype,
    register_cuda_available_resolver,
    register_torch_dtype_resolver,
    register_torch_resolvers,
)

# Contracts: §9 Environment.


class FakeDtype:
    pass


FAKE_TORCH = ModuleType("torch")
FAKE_TORCH.__dict__.update(
    dtype=FakeDtype,
    float32=FakeDtype(),
    pi=3.14,
    cuda=SimpleNamespace(is_available=lambda: False),
)


@pytest.fixture
def fake_torch(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", FAKE_TORCH)


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


def test_torch_resolvers_resolve_with_fake_torch(fake_torch):
    register_torch_resolvers()
    cfg = OmegaConf.create({"dtype": "${dtype:float32}", "cuda": "${cuda_available:}"})
    assert cfg.dtype is FAKE_TORCH.float32
    assert cfg.cuda is False


@pytest.mark.parametrize("name", ["not_a_dtype", "pi"])
def test_torch_dtype_resolver_rejects_non_dtypes(fake_torch, name):
    register_torch_dtype_resolver()
    cfg = OmegaConf.create({"dtype": f"${{dtype:{name}}}"})
    with pytest.raises(InterpolationResolutionError, match="Invalid torch dtype"):
        _ = cfg.dtype


def test_torch_individual_resolvers_register_one_name(fake_torch):
    register_torch_dtype_resolver()
    assert OmegaConf.has_resolver("dtype")
    assert not OmegaConf.has_resolver("cuda_available")
    register_cuda_available_resolver()
    assert OmegaConf.has_resolver("cuda_available")


def test_torch_conflict_does_not_partially_register_with_fake_torch(fake_torch):
    OmegaConf.register_new_resolver("cuda_available", lambda: True)
    with pytest.raises(ValueError, match="already registered"):
        register_torch_resolvers()
    assert not OmegaConf.has_resolver("dtype")


def test_torch_replace_overwrites_existing_resolvers(fake_torch):
    OmegaConf.register_new_resolver("cuda_available", lambda: True)
    register_torch_resolvers(replace=True)
    assert OmegaConf.create({"cuda": "${cuda_available:}"}).cuda is False
