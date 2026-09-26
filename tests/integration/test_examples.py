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
