import os
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from omegakit import instantiate, load_config, validate
from omegakit.resolvers.paths import register_paths_resolver
from omegakit.resolvers.secrets import register_secret_resolver
from omegakit.resolvers.torch import register_torch_resolvers

DOCS = Path(__file__).parents[2] / "docs"
EXAMPLE = DOCS / "example"
# Every docs section except the ones that test_examples.py runs as a whole.
SECTIONS = [
    path
    for path in DOCS.iterdir()
    if path.is_dir() and path.name not in {"_build", "example"}
]
YAML_FILES = sorted(path for section in SECTIONS for path in section.rglob("*.yaml"))
SCRIPTS = sorted(path for section in SECTIONS for path in section.rglob("main.py"))


@pytest.fixture(autouse=True)
def examples_importable(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE))


def _needs_torch(text: str) -> bool:
    # The PyTorch example and the Torch resolvers need the docs-examples group.
    return any(
        name in text for name in ("project", "torch", "${dtype:", "${cuda_available:")
    )


@pytest.mark.parametrize(
    "path", YAML_FILES, ids=[str(p.relative_to(DOCS)) for p in YAML_FILES]
)
def test_guide_yaml_loads_validates_and_builds(path: Path, monkeypatch):
    # The secrets page reads a token from the environment, and the paths page
    # names directories through the paths resolver.
    monkeypatch.setenv("TRACKER_TOKEN", "tok-for-the-guide-tests")
    register_secret_resolver()
    register_paths_resolver({"runs": "runs", "data": "data"})
    if _needs_torch(path.read_text()):
        pytest.importorskip("torch")
        register_torch_resolvers()
    config = load_config(path)
    validate(config, allow_missing=True)
    if "$class" in config and not OmegaConf.missing_keys(config):
        instantiate(config)


@pytest.mark.parametrize(
    "script", SCRIPTS, ids=[str(p.parent.relative_to(DOCS)) for p in SCRIPTS]
)
def test_guide_script_runs(script: Path):
    if _needs_torch(script.read_text()):
        pytest.importorskip("torch")
    subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        env={
            **os.environ,
            "PYTHONPATH": str(EXAMPLE),
        },
        check=True,
    )
