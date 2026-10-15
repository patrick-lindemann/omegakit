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

pytestmark = pytest.mark.docs

DOCS = Path(__file__).parents[2] / "docs"
EXAMPLE = DOCS / "example"
EXAMPLE_EXPERIMENTS = sorted((EXAMPLE / "configs" / "experiments").glob("*.yaml"))
# Pages with shell sessions, and the directory the sessions run in, which the test
# copies first.
SESSION_PAGES = {
    "getting-started": EXAMPLE,
    "command-line/check": EXAMPLE,
    "command-line/show": EXAMPLE,
    "recipes/checking-experiments-in-ci": EXAMPLE,
    "security/secrets": DOCS / "security" / "secrets",
}
PROGRAMS = {"python": [sys.executable], "omegakit": [sys.executable, "-m", "omegakit"]}
COMMAND_BLOCK = r"```sh\n(.*?)\n```\n\n"
OUTPUT_BLOCK = r"```\{code-block\} text\n:caption: Output\n\n(.*?)```"


def test_readme_example_builds(tmp_path: Path) -> None:
    readme = (Path(__file__).parents[2] / "README.md").read_text()
    for name, text in re.findall(
        r"```(?:yaml|python)\n# (\S+)\n(.*?)```", readme, re.S
    ):
        (tmp_path / name).write_text(text)
    with (tmp_path / "main.py").open("a") as main_file:
        main_file.write("print(type(model).__name__, type(optimizer).__name__)\n")
    output = subprocess.run(
        [sys.executable, "main.py"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert output == "Linear SGD\n"


@pytest.mark.parametrize("experiment", EXAMPLE_EXPERIMENTS, ids=lambda path: path.stem)
def test_example_experiment_runs(experiment: Path, tmp_path: Path) -> None:
    output = _train(experiment, cwd=tmp_path)
    assert output.startswith(f"{experiment.stem}: test loss ")
    run_dir = tmp_path / "runs" / experiment.stem / "seed0"
    assert sorted(file_path.name for file_path in run_dir.iterdir()) == [
        "config.yaml",
        "model.pt",
        "overrides.txt",
    ]


def test_example_run_repeats_from_its_saved_config(tmp_path: Path) -> None:
    first = _train(
        EXAMPLE / "configs/experiments/mlp.yaml", "model.hidden=8", cwd=tmp_path
    )
    saved_dir = tmp_path / "runs" / "mlp" / "seed0"
    assert (saved_dir / "overrides.txt").read_text() == "model.hidden=8\n"
    assert _train(saved_dir / "config.yaml", "run_dir=repeat", cwd=tmp_path) == first
    weights = (saved_dir / "model.pt").read_bytes()
    assert (tmp_path / "repeat" / "model.pt").read_bytes() == weights


def test_example_seed_changes_the_run(tmp_path: Path) -> None:
    experiment = EXAMPLE / "configs/experiments/mlp.yaml"
    assert _train(experiment, cwd=tmp_path) != _train(
        experiment, "seed=1", cwd=tmp_path
    )


def test_example_never_overwrites_a_run(tmp_path: Path) -> None:
    _train(EXAMPLE_EXPERIMENTS[0], cwd=tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        _train(EXAMPLE_EXPERIMENTS[0], cwd=tmp_path)


@pytest.mark.parametrize("page", SESSION_PAGES)
def test_page_sessions_show_real_output(
    page: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRACKER_TOKEN", "tok-5f3a9c1e7b2d4f60")
    shutil.copytree(
        SESSION_PAGES[page],
        tmp_path,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("runs", "__pycache__"),
    )
    text = (DOCS / page / "index.md").read_text()
    # A command block, and the Output block right after it if the command prints.
    sessions = re.findall(f"{COMMAND_BLOCK}(?:{OUTPUT_BLOCK})?", text, re.S)
    sessions = [
        (command, output)
        for command, output in sessions
        if command.split()[0] in PROGRAMS
    ]
    assert sessions
    for command, output in sessions:
        program, *arguments = shlex.split(command)
        arguments = [
            name
            for argument in arguments
            for name in (
                sorted(glob.glob(argument, root_dir=tmp_path))
                if "*" in argument
                else [argument]
            )
        ]
        # What a terminal shows: `check` and `show` print a failure to stderr.
        result = subprocess.run(
            [*PROGRAMS[program], *arguments],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert (command, result.stdout) == (command, output)


def test_ci_recipe_test_file_passes() -> None:
    test_file = DOCS / "recipes" / "checking-experiments-in-ci" / "test_experiments.py"
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", test_file],
        env={**os.environ, "PYTHONPATH": str(EXAMPLE)},
        check=True,
        capture_output=True,
    )


def _train(*arguments: object, cwd: Path) -> str:
    return subprocess.run(
        [sys.executable, str(EXAMPLE / "main.py"), *map(str, arguments)],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(EXAMPLE)},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
