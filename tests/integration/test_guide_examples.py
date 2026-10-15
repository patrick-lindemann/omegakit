import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from omegakit import TARGET_KEY, ConfigLoadError, instantiate, load_config, validate
from omegakit.resolvers.paths import register_paths_resolver
from omegakit.resolvers.secrets import register_secret_resolver
from omegakit.resolvers.torch import register_torch_resolvers

pytestmark = pytest.mark.docs

DOCS = Path(__file__).parents[2] / "docs"
EXAMPLE = DOCS / "example"
# Every docs section except the example project, which test_examples.py runs.
SECTIONS = [
    section_dir
    for section_dir in DOCS.iterdir()
    if section_dir.is_dir() and section_dir.name not in {"_build", "example"}
]
# Files that show an error on their page, and so must not load.
INVALID_YAML_FILES = {DOCS / "guide" / "errors" / "broken.yaml"}
YAML_FILES = sorted(
    file_path
    for section_dir in [*SECTIONS, EXAMPLE]
    for file_path in section_dir.rglob("*.yaml")
    if file_path not in INVALID_YAML_FILES
)
SCRIPTS = sorted(
    file_path for section_dir in SECTIONS for file_path in section_dir.rglob("main.py")
)
# The tests of the pages that stages 3 to 6 of the docs rewrite have not rewritten
# yet, with the stage that rewrites each. A stage removes the items of its pages.
EXPECTED_FAILURES = {
    "example/configs/base.yaml": "stage 5, renamed `$class`",
    "example/configs/experiments/linear.yaml": "stage 5, renamed `~import`",
    "example/configs/experiments/mlp.yaml": "stage 5, renamed `~import`",
    "getting-started/experiment.yaml": "stage 5, renamed `$class`",
    "resolvers/torch/precision.yaml": "stage 6, renamed torch resolvers",
    "security/restricting-imports/shared-run/config.yaml": "stage 6, renamed `$class`",
    "getting-started": "stage 5, renamed `$class`",
    "recipes/parameter-sweeps": "stage 5, renamed `~import`",
    "recipes/swapping-implementations": "stage 5, renamed `~import`",
    "resolvers/torch": "stage 6, renamed torch resolvers",
    "security/restricting-imports": "stage 6, removed `import_root`",
}


@pytest.fixture(autouse=True)
def expected_failure(request: pytest.FixtureRequest) -> None:
    reason = EXPECTED_FAILURES.get(request.node.callspec.id)
    if reason is not None:
        request.applymarker(pytest.mark.xfail(reason=reason, strict=True))


@pytest.fixture(autouse=True)
def examples_importable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(EXAMPLE))


@pytest.mark.parametrize(
    "file_path",
    YAML_FILES,
    ids=[str(file_path.relative_to(DOCS)) for file_path in YAML_FILES],
)
def test_guide_yaml_loads_validates_and_builds(
    file_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The secrets page reads a token from the environment, and the paths page
    # names directories through the paths resolver.
    monkeypatch.setenv("TRACKER_TOKEN", "tok-for-the-guide-tests")
    register_secret_resolver(replace=True)
    register_paths_resolver({"runs": "runs", "data": "data"}, replace=True)
    register_torch_resolvers(replace=True)
    # A page's classes live next to its files, such as `models.py`.
    monkeypatch.syspath_prepend(str(file_path.parent))
    config = load_config(file_path)
    validate(config, allow_missing=True)
    if TARGET_KEY in config and not OmegaConf.missing_keys(config):
        instantiate(config)


@pytest.mark.parametrize(
    "script",
    SCRIPTS,
    ids=[str(script.parent.relative_to(DOCS)) for script in SCRIPTS],
)
def test_guide_script_output_is_on_its_page(script: Path) -> None:
    output = subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        env={**os.environ, "PYTHONPATH": str(EXAMPLE)},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    page = (script.parent / "index.md").read_text()
    # The Output blocks of the script, not those that follow a shell command.
    page = re.sub(
        r"```sh\n[^`]*```\n\n```\{code-block\} text\n:caption: Output\n.*?```",
        "",
        page,
        flags=re.S,
    )
    shown = re.findall(r":caption: Output\n\n(.*?)```", page, re.S)
    if shown or output:
        assert "".join(shown) == output


@pytest.mark.parametrize(
    "file_path",
    sorted(INVALID_YAML_FILES),
    ids=lambda file_path: str(file_path.relative_to(DOCS)),
)
def test_guide_invalid_yaml_does_not_load(file_path: Path) -> None:
    with pytest.raises(ConfigLoadError):
        load_config(file_path)
