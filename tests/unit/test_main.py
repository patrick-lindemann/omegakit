import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
import yaml

from omegakit.__main__ import main


def test_runs_as_a_module_without_warnings(tmp_path: Path):
    path = tmp_path / "a.yaml"
    path.write_text("x: 1\n")
    result = subprocess.run(
        [sys.executable, "-W", "error", "-m", "omegakit", "show", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert yaml.safe_load(result.stdout) == {"x": 1}


def test_prints_the_version(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert capsys.readouterr().out == f"omegakit {version('omegakit')}\n"


def test_needs_a_command():
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2
