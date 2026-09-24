import subprocess
import sys
from pathlib import Path

import pytest

# Runs every script in docs/examples/ as `__main__`, the way a reader would.

EXAMPLES = sorted(Path(__file__).parents[2].joinpath("docs", "examples").glob("*.py"))


@pytest.mark.parametrize("example", EXAMPLES, ids=[path.stem for path in EXAMPLES])
def test_example_runs(example: Path):
    subprocess.run([sys.executable, str(example)], check=True)
