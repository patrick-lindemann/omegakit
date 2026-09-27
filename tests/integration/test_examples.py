import os
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
