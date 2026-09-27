import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Runs the getting-started and webapp scripts as a reader would, from anywhere.

DOCS = Path(__file__).parents[2] / "docs"
EXAMPLES = [DOCS / "getting-started" / "main.py", DOCS / "webapp" / "main.py"]


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
        code.group(1) + "print(type(app.database).__name__, app.server.secret_key)\n"
    )
    output = subprocess.run(
        [sys.executable, "main.py"],
        cwd=tmp_path,
        env={**os.environ, "SECRET_KEY": "s3cret", "PYTHONPATH": str(WEBAPP.parent)},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert output == "Postgres s3cret\n"


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_webapp_tests_pass(environment):
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=WEBAPP.parent,
        env={**os.environ, "APP_ENV": environment, "SECRET_KEY": "prod-secret-value"},
        check=True,
    )


COMMANDS = [
    (
        "check configs/app.yaml --schema webapp.App --allow-module webapp",
        0,
        "",
    ),
    (
        "check configs/app.yaml server.workers=many --schema webapp.App",
        1,
        "configs/app.yaml: ConfigValidationError: Invalid config in `server.workers` "
        "(ServerConfig): Value 'many' of type 'str' could not be converted to "
        "Integer\n",
    ),
    (
        "check configs/base.yaml --schema webapp.App --allow-missing",
        0,
        "",
    ),
    (
        "show configs/app.yaml --node server",
        0,
        "$class: webapp.server.Server\nhost: 127.0.0.1\nport: 8000\nworkers: 1\n"
        "secret_key: '***'\n",
    ),
    (
        "show configs/app.yaml server.host=example.com --node cache.url --resolve",
        0,
        "redis://example.com:6379\n",
    ),
]


@pytest.mark.parametrize(("command", "code", "output"), COMMANDS)
def test_command_line_guide_output(command, code, output):
    result = subprocess.run(
        [sys.executable, "-m", "omegakit", *command.split()],
        cwd=WEBAPP.parent,
        env={k: v for k, v in os.environ.items() if k != "APP_ENV"},
        capture_output=True,
        text=True,
    )
    assert (result.returncode, result.stdout) == (code, output)
