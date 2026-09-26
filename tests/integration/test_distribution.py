import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
UV = os.environ.get("UV") or shutil.which("uv")

SCRIPT = """
import sys
from pathlib import Path

import omegakit

assert Path(omegakit.__file__).is_relative_to(sys.prefix), omegakit.__file__
config = omegakit.load_config("app.yaml", overrides=["hours=3"])
print(omegakit.instantiate(config))
"""


@pytest.mark.distribution
@pytest.mark.skipif(UV is None, reason="needs uv")
def test_installed_wheel(tmp_path: Path):
    assert UV is not None
    subprocess.run(
        [UV, "build", "--wheel", "--no-sources", "--out-dir", tmp_path / "dist"],
        cwd=ROOT,
        check=True,
    )
    constraints = tmp_path / "constraints.txt"
    subprocess.run(
        [
            UV,
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            "--output-file",
            constraints,
        ],
        cwd=ROOT,
        check=True,
    )
    venv = tmp_path / "venv"
    subprocess.run([UV, "venv", "--python", sys.executable, venv], check=True)
    python = venv / "bin" / "python"
    subprocess.run(
        [
            UV,
            "pip",
            "install",
            "--python",
            python,
            "--constraints",
            constraints,
            *(tmp_path / "dist").glob("*.whl"),
        ],
        check=True,
    )
    (tmp_path / "app.yaml").write_text(
        "$class: datetime.timedelta\ndays: 1\nhours: 2\n"
    )

    help_text = subprocess.run(
        [venv / "bin" / "omegakit", "--help"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    built = subprocess.run(
        [python, "-c", SCRIPT],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "check" in help_text
    assert built == "1 day, 3:00:00\n"
