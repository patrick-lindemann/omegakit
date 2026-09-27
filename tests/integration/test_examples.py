import glob
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from omegakit import instantiate

# Runs the example applications as a reader would, from anywhere.

DOCS = Path(__file__).parents[2] / "docs"
EXAMPLES = [DOCS / "webapp" / "main.py"]


@pytest.mark.parametrize(
    "example", EXAMPLES, ids=[path.parent.name for path in EXAMPLES]
)
def test_example_runs(example: Path):
    subprocess.run([sys.executable, str(example)], check=True)


WEBAPP = DOCS / "webapp" / "main.py"


@pytest.mark.parametrize(
    ("environment", "database"), [("dev", "SQLite"), ("prod", "Postgres")]
)
def test_webapp_builds_in_each_environment(environment, database):
    output = subprocess.run(
        [sys.executable, str(WEBAPP), "server.port=9000"],
        env={**os.environ, "APP_ENV": environment, "SECRET_KEY": "prod-secret-value"},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert f"database: {database} " in output
    assert ":9000 " in output
    assert "prod-secret-value" not in output


def test_readme_example_builds(tmp_path):
    readme = (Path(__file__).parents[2] / "README.md").read_text()
    for name, text in re.findall(r"```yaml\n# (\S+)\n(.*?)```", readme, re.S):
        (tmp_path / name).write_text(text)
    code = re.search(r"```python\n(.*?)```", readme, re.S)
    assert code is not None
    (tmp_path / "main.py").write_text(
        code.group(1)
        + "print(type(experiment.model).__name__, len(experiment.data.samples()[0]))\n"
    )
    output = subprocess.run(
        [sys.executable, "main.py"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(DOCS / "curvefit")},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert output == "Polynomial 200\n"


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_webapp_tests_pass(environment):
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=WEBAPP.parent,
        env={**os.environ, "APP_ENV": environment, "SECRET_KEY": "prod-secret-value"},
        check=True,
    )


CURVEFIT = DOCS / "curvefit"
EXPERIMENTS = sorted((CURVEFIT / "configs" / "experiments").glob("*.yaml"))


def _fit(*arguments: object, cwd: Path) -> str:
    return subprocess.run(
        [sys.executable, str(CURVEFIT / "main.py"), *map(str, arguments)],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.mark.parametrize("experiment", EXPERIMENTS, ids=lambda path: path.stem)
def test_curvefit_experiment_runs(experiment, tmp_path):
    output = _fit(experiment, cwd=tmp_path)
    assert output.startswith(f"{experiment.stem}: train loss ")
    run_dir = tmp_path / "runs" / experiment.stem / "seed0"
    assert sorted(path.name for path in run_dir.iterdir()) == [
        "config.yaml",
        "metrics.jsonl",
        "overrides.txt",
    ]


def test_curvefit_run_repeats_from_its_saved_config(tmp_path):
    first = _fit(EXPERIMENTS[-1], "model.degree=4", cwd=tmp_path)
    saved = tmp_path / "runs" / "poly3-adam" / "seed0"
    assert (saved / "overrides.txt").read_text() == "model.degree=4\n"
    assert _fit(saved / "config.yaml", "run_dir=repeat", cwd=tmp_path) == first
    metrics = (saved / "metrics.jsonl").read_text()
    assert (tmp_path / "repeat" / "metrics.jsonl").read_text() == metrics


def test_curvefit_seed_changes_the_run(tmp_path):
    assert _fit(EXPERIMENTS[-1], cwd=tmp_path) != _fit(
        EXPERIMENTS[-1], "seed=1", cwd=tmp_path
    )


def test_curvefit_never_overwrites_a_run(tmp_path):
    _fit(EXPERIMENTS[0], cwd=tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        _fit(EXPERIMENTS[0], cwd=tmp_path)


def test_curvefit_measurements_load(monkeypatch):
    monkeypatch.syspath_prepend(str(CURVEFIT))
    path = CURVEFIT / "data" / "measurements.csv"
    xs, ys = instantiate(
        {"$class": "curvefit.data.CsvData", "path": str(path)}
    ).samples()
    assert len(xs) == len(ys) == 40


@pytest.mark.parametrize("dtype", ["float32", "bfloat16"])
def test_curvefit_torch_variant_runs(dtype, tmp_path):
    # Only the `test-resolvers` CI job installs Torch.
    pytest.importorskip("torch")
    output = subprocess.run(
        [
            sys.executable,
            str(CURVEFIT / "torch" / "main.py"),
            f"model.dtype=${{dtype:{dtype}}}",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(CURVEFIT)},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert output.startswith(f"poly3-adam-torch: Adam, torch.{dtype}\n")


# Pages whose shell sessions run in a copy of the curvefit directory, and pages
# whose sessions only read files and run in their own directory.
SESSION_PAGES = [
    "getting-started",
    "reproducible-runs",
    "command-line",
    "schemas/editor-support",
    "recipes/checking-experiments-in-ci",
]
READ_ONLY_SESSION_PAGES = ["security/secrets"]
PROGRAMS = {"python": [sys.executable], "omegakit": [sys.executable, "-m", "omegakit"]}


@pytest.mark.parametrize("page", SESSION_PAGES + READ_ONLY_SESSION_PAGES)
def test_page_sessions_show_real_output(page, tmp_path, monkeypatch):
    monkeypatch.setenv("TRACKER_TOKEN", "tok-5f3a9c1e7b2d4f60")
    directory = DOCS / page
    if page in SESSION_PAGES:
        shutil.copytree(
            CURVEFIT,
            tmp_path,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("runs", "__pycache__"),
        )
        directory = tmp_path
    text = (DOCS / page / "index.md").read_text()
    sessions = re.findall(r"```text\n(\$ .*?)```", text, re.S)
    assert sessions
    for session in sessions:
        for command, output in re.findall(
            r"^\$ (.*)\n((?:(?!\$ ).*\n)*)", session, re.M
        ):
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
