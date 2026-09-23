import importlib.metadata

project = "omegakit"
author = "Patrick Lindemann"
copyright = "2026, Patrick Lindemann"  # noqa: A001 (Sphinx setting)
release = importlib.metadata.version("omegakit")

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

# Markdown-style backticks in docstrings render as inline code.
default_role = "code"
exclude_patterns = ["_build"]
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
napoleon_google_docstring = True
napoleon_numpy_docstring = False
autodoc_member_order = "bysource"
html_theme = "furo"
html_title = "omegakit"
