import glob
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Runs the example project and the README as a reader would.

DOCS = Path(__file__).parents[2] / "docs"


def test_readme_example_builds(tmp_path):
    pytest.importorskip("torch")
    readme = (Path(__file__).parents[2] / "README.md").read_text()
    for name, text in re.findall(r"```yaml\n# (\S+)\n(.*?)```", readme, re.S):
        (tmp_path / name).write_text(text)
    code = re.search(r"```python\n(.*?)```", readme, re.S)
    assert code is not None
    (tmp_path / "main.py").write_text(
        code.group(1)
        + "print(type(experiment.model).__name__, type(optimizer).__name__)\n"
    )
    output = subprocess.run(
        [sys.executable, "main.py"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert output == "Linear SGD\n"


EXAMPLE = DOCS / "example"
EXAMPLE_EXPERIMENTS = sorted((EXAMPLE / "configs" / "experiments").glob("*.yaml"))


def _train(*arguments: object, cwd: Path) -> str:
    pytest.importorskip("torch")
    return subprocess.run(
        [sys.executable, str(EXAMPLE / "main.py"), *map(str, arguments)],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(EXAMPLE)},
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.mark.parametrize("experiment", EXAMPLE_EXPERIMENTS, ids=lambda path: path.stem)
def test_example_experiment_runs(experiment, tmp_path):
    output = _train(experiment, cwd=tmp_path)
    assert output.startswith(f"{experiment.stem}: test loss ")
    run_dir = tmp_path / "runs" / experiment.stem / "seed0"
    assert sorted(path.name for path in run_dir.iterdir()) == [
        "config.yaml",
        "model.pt",
        "overrides.txt",
    ]


def test_example_run_repeats_from_its_saved_config(tmp_path):
    first = _train(
        EXAMPLE / "configs/experiments/mlp.yaml", "model.hidden=8", cwd=tmp_path
    )
    saved = tmp_path / "runs" / "mlp" / "seed0"
    assert (saved / "overrides.txt").read_text() == "model.hidden=8\n"
    assert _train(saved / "config.yaml", "run_dir=repeat", cwd=tmp_path) == first
    weights = (saved / "model.pt").read_bytes()
    assert (tmp_path / "repeat" / "model.pt").read_bytes() == weights


def test_example_seed_changes_the_run(tmp_path):
    experiment = EXAMPLE / "configs/experiments/mlp.yaml"
    assert _train(experiment, cwd=tmp_path) != _train(
        experiment, "seed=1", cwd=tmp_path
    )


def test_example_never_overwrites_a_run(tmp_path):
    _train(EXAMPLE_EXPERIMENTS[0], cwd=tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        _train(EXAMPLE_EXPERIMENTS[0], cwd=tmp_path)


# Pages whose shell sessions run in a copy of the example project, and pages whose
# sessions only read files and run in their own directory.
# Pages with shell sessions, and the directory the sessions run in, which the test
# copies first.
SESSION_PAGES = {
    "getting-started": EXAMPLE,
    "command-line": EXAMPLE,
    "recipes/checking-experiments-in-ci": EXAMPLE,
    "schemas/editor-support": DOCS / "schemas" / "editor-support",
    "security/secrets": DOCS / "security" / "secrets",
}
PROGRAMS = {"python": [sys.executable], "omegakit": [sys.executable, "-m", "omegakit"]}
COMMAND_BLOCK = r"```sh\n(.*?)\n```\n\n"
OUTPUT_BLOCK = r"```\{code-block\} text\n:caption: Output\n\n(.*?)```"


@pytest.mark.parametrize("page", SESSION_PAGES)
def test_page_sessions_show_real_output(page, tmp_path, monkeypatch):
    monkeypatch.setenv("TRACKER_TOKEN", "tok-5f3a9c1e7b2d4f60")
    pytest.importorskip("torch")
    shutil.copytree(
        SESSION_PAGES[page],
        tmp_path,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("runs", "__pycache__"),
    )
    directory = tmp_path
    text = (DOCS / page / "index.md").read_text()
    # A command block, and the Output block right after it if the command prints.
    commands = re.findall(f"{COMMAND_BLOCK}(?:{OUTPUT_BLOCK})?", text, re.S)
    commands = [(c, output) for c, output in commands if c.split()[0] in PROGRAMS]
    assert commands
    for command, output in commands:
        program, *arguments = shlex.split(command)
        arguments = [
            name
            for argument in arguments
            for name in (
                sorted(glob.glob(argument, root_dir=directory))
                if "*" in argument
                else [argument]
            )
        ]
        result = subprocess.run(
            [*PROGRAMS[program], *arguments],
            cwd=directory,
            capture_output=True,
            text=True,
        )
        assert (command, result.stdout) == (command, output)


def test_ci_recipe_test_file_passes():
    pytest.importorskip("torch")
    test_file = DOCS / "recipes" / "checking-experiments-in-ci" / "test_experiments.py"
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", test_file],
        env={**os.environ, "PYTHONPATH": str(EXAMPLE)},
        check=True,
        capture_output=True,
    )
