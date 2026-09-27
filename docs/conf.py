import importlib.metadata

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
exclude_patterns = ["_build"]
myst_heading_anchors = 3
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
napoleon_google_docstring = True
napoleon_numpy_docstring = False
autodoc_member_order = "bysource"
html_theme = "furo"
html_title = "omegakit"
# Old page names to their new pages, so that links to earlier releases keep working.
redirects = {
    "guide/instantiation": "building-objects.html",
    "guide/metadata": "building-objects.html#meta",
    "guide/configurable": "typed-configs.html#a-custom-from-config",
    "guide/walk": "../api.html#traversal",
    "cookbook": "recipes/swapping.html",
    "contracts": "guide/loading.html#rules",
    "contracts/assembly": "../guide/loading.html#rules",
    "contracts/instantiation": "../guide/building-objects.html#rules",
    "contracts/typed-configs": "../guide/typed-configs.html#rules",
    "contracts/command-line": "../guide/command-line.html#rules",
    "contracts/errors": "../errors.html",
    "recipes/environments": "../getting-started.html",
    "contracts/environment": "../security.html",
}
