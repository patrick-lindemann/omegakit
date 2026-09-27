import os
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from omegakit import instantiate, load_config, validate

EXAMPLES = Path(__file__).parents[2] / "docs" / "examples"
WEBAPP = EXAMPLES / "webapp"
YAML_FILES = sorted((EXAMPLES / "guide").glob("*/**/*.yaml"))
SCRIPTS = sorted((EXAMPLES / "guide").glob("*/main.py"))


@pytest.fixture(autouse=True)
def webapp_importable(monkeypatch):
    monkeypatch.syspath_prepend(str(WEBAPP))


@pytest.mark.parametrize(
    "path", YAML_FILES, ids=[str(p.relative_to(EXAMPLES)) for p in YAML_FILES]
)
def test_guide_yaml_loads_validates_and_builds(path: Path):
    config = load_config(path)
    validate(config, allow_missing=True)
    if "$class" in config and not OmegaConf.missing_keys(config):
        instantiate(config)


@pytest.mark.parametrize("script", SCRIPTS, ids=[p.parent.name for p in SCRIPTS])
def test_guide_script_runs(script: Path):
    subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        env={**os.environ, "PYTHONPATH": str(WEBAPP)},
        check=True,
    )
