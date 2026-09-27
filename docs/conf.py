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
    "guide/base": "base/index.html",
    "guide/building-objects": "building-objects/index.html",
    "guide/command-line": "command-line/index.html",
    "guide/defaults": "defaults/index.html",
    "guide/editor-schemas": "editor-schemas/index.html",
    "guide/imports": "imports/index.html",
    "guide/interpolation-and-missing": "interpolation-and-missing/index.html",
    "guide/loading": "loading/index.html",
    "guide/overrides": "overrides/index.html",
    "guide/resolvers": "resolvers/index.html",
    "guide/typed-configs": "typed-configs/index.html",
    "guide/validation": "validation/index.html",
    "recipes/manifests": "manifests/index.html",
    "recipes/swapping": "swapping/index.html",
    "recipes/tenants": "tenants/index.html",
    "getting-started": "getting-started/index.html",
    "security": "security/index.html",
    "guide/instantiation": "building-objects/index.html",
    "guide/metadata": "building-objects/index.html#meta",
    "guide/configurable": "typed-configs/index.html#a-custom-from-config",
    "guide/walk": "../api.html#traversal",
    "cookbook": "recipes/swapping/index.html",
    "contracts": "guide/loading/index.html#rules",
    "contracts/assembly": "../guide/loading/index.html#rules",
    "contracts/instantiation": "../guide/building-objects/index.html#rules",
    "contracts/typed-configs": "../guide/typed-configs/index.html#rules",
    "contracts/command-line": "../guide/command-line/index.html#rules",
    "contracts/errors": "../errors.html",
    "recipes/environments": "../getting-started/index.html",
    "contracts/environment": "../security/index.html",
}
