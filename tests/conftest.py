import functools
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from omegaconf import OmegaConf


@pytest.fixture(autouse=True)
def clear_resolvers():
    OmegaConf.clear_resolvers()
    yield
    OmegaConf.clear_resolvers()


@pytest.fixture
def write_yaml(tmp_path: Path) -> Callable[[str, str], Path]:
    return functools.partial(_write_yaml, tmp_path)


def _write_yaml(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text))
    return path
