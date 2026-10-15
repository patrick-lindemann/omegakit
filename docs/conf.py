import importlib
import importlib.metadata
import pkgutil
from typing import Any, TypeAliasType

from sphinx.application import Sphinx
from sphinx.config import Config as SphinxConfig
from sphinx.pycode import ModuleAnalyzer
from sphinx_autodoc_typehints import format_annotation

import omegakit

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
# `typehints_formatter` is a function, which Sphinx cannot cache.
suppress_warnings = ["config.cache"]


def setup(app: Sphinx) -> None:
    app.connect("autodoc-process-docstring", _use_source_docstring)


def typehints_formatter(annotation: Any, config: SphinxConfig) -> str | None:
    # A type alias is shown by its name if `omegakit` exports it, else by its value,
    # since the extension shows every alias as `TypeAliasType`.
    if not isinstance(annotation, TypeAliasType):
        return None
    if getattr(omegakit, annotation.__name__, None) is annotation:
        return f":py:data:`~omegakit.{annotation.__name__}`"
    return format_annotation(annotation.__value__, config, short_literals=True)


def _use_source_docstring(
    app: Sphinx, what: str, name: str, obj: Any, options: Any, lines: list[str]
) -> None:
    # A constant re-exported by `omegakit` has its docstring in the module that
    # defines it, which autodoc does not search, so it shows that of its type.
    if what == "data" and name in _SOURCE_DOCSTRINGS:
        lines[:] = _SOURCE_DOCSTRINGS[name]


def _read_source_docstrings() -> dict[str, list[str]]:
    docstrings: dict[str, list[str]] = {}
    core = importlib.import_module("omegakit._core")
    for module_info in pkgutil.walk_packages(core.__path__, "omegakit._core."):
        attribute_docs = ModuleAnalyzer.for_module(module_info.name).find_attr_docs()
        for (_, attribute), docstring in attribute_docs.items():
            if attribute in omegakit.__all__:
                docstrings[f"omegakit.{attribute}"] = list(docstring)
    return docstrings


_SOURCE_DOCSTRINGS = _read_source_docstrings()
