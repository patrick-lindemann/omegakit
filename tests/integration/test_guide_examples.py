import os
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from omegakit import instantiate, load_config, validate

DOCS = Path(__file__).parents[2] / "docs"
WEBAPP = DOCS / "webapp"
CURVEFIT = DOCS / "curvefit"
# Every docs section except the ones that test_examples.py runs as a whole.
SECTIONS = [
    path
    for path in DOCS.iterdir()
    if path.is_dir()
    and path.name not in {"_build", "webapp", "curvefit", "getting-started"}
]
YAML_FILES = sorted(path for section in SECTIONS for path in section.rglob("*.yaml"))
SCRIPTS = sorted(path for section in SECTIONS for path in section.rglob("main.py"))


@pytest.fixture(autouse=True)
def examples_importable(monkeypatch):
    monkeypatch.syspath_prepend(str(WEBAPP))
    monkeypatch.syspath_prepend(str(CURVEFIT))


@pytest.mark.parametrize(
    "path", YAML_FILES, ids=[str(p.relative_to(DOCS)) for p in YAML_FILES]
)
def test_guide_yaml_loads_validates_and_builds(path: Path):
    config = load_config(path)
    validate(config, allow_missing=True)
    if "$class" in config and not OmegaConf.missing_keys(config):
        instantiate(config)


@pytest.mark.parametrize(
    "script", SCRIPTS, ids=[str(p.parent.relative_to(DOCS)) for p in SCRIPTS]
)
def test_guide_script_runs(script: Path):
    subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        env={**os.environ, "PYTHONPATH": os.pathsep.join([str(WEBAPP), str(CURVEFIT)])},
        check=True,
    )
