import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

project = "omegakit"
author = "Patrick Lindemann, Mustafa Mohsen"
copyright = "2026, Patrick Lindemann, Mustafa Mohsen"  # noqa: A001 (Sphinx setting)
release = importlib.metadata.version("omegakit")

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_reredirects",
]

# Markdown-style backticks in docstrings render as inline code.
default_role = "code"
exclude_patterns = ["_build", "_generated"]
myst_heading_anchors = 3
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
napoleon_google_docstring = True
napoleon_numpy_docstring = False
autodoc_member_order = "bysource"
html_theme = "furo"
html_title = "omegakit"
redirects = {}

# The command-line page shows each command's `--help`, generated here so that it
# never goes stale.
_generated = Path(__file__).parent / "_generated"
_generated.mkdir(exist_ok=True)
for _command in ("check", "show", "json-schema"):
    (_generated / f"{_command}.txt").write_text(
        subprocess.run(
            [sys.executable, "-m", "omegakit", _command, "--help"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "COLUMNS": "88"},
        ).stdout
    )
