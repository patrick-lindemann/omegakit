META_KEY = "$meta"
"""Metadata attached to a node."""

IMPORT_KEY = "~import"
"""Value prefix that replaces a node with another config file or one of its nodes."""

BASE_KEY = "$base"
"""A mapping, or a list of mappings, merged underneath the node."""

DEFAULTS_KEY = "$defaults"
"""A mapping merged underneath every dict-valued sibling."""

CLASS_KEY = "$class"
"""Import path of the class or function a node is built with."""

REF_KEY = "$ref"
"""Import path of an object that replaces the node without being called."""

PARTIAL_KEY = "$partial"
"""Flag that builds a `functools.partial` instead of calling the class."""
