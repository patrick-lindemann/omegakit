import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Runs every docs/examples/<name>/main.py as a script, the way a reader would.

EXAMPLES = sorted(
    Path(__file__).parents[2].joinpath("docs", "examples").glob("*/main.py")
)


@pytest.mark.parametrize(
    "example", EXAMPLES, ids=[path.parent.name for path in EXAMPLES]
)
def test_example_runs(example: Path):
    subprocess.run([sys.executable, str(example)], check=True)


WEBAPP = Path(__file__).parents[2] / "docs" / "examples" / "webapp" / "main.py"


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
