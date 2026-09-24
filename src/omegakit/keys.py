META_KEY = "$meta"
"""Metadata attached to a node, dropped on load unless `keep_meta=True`.

For example `$meta: {author: myname}`. It is never passed to a constructor.
"""

IMPORT_KEY = "~import"
"""Value prefix that replaces a node with another config file or one of its nodes.

For example `~import models/base.yaml#optimizer`. See §7 of the configuration
contracts.
"""

BASE_KEY = "$base"
"""A mapping, or a list of mappings, merged underneath the node.

For example `$base: ~import defaults.yaml`. See §2 of the configuration contracts.
"""

DEFAULTS_KEY = "$defaults"
"""A mapping merged underneath every dict-valued sibling.

For example `$defaults: {path: data/${.id}.h5}`. See §2 of the configuration
contracts.
"""

CLASS_KEY = "$class"
"""Import path of the class or function a node is built with.

For example `$class: myapp.models.Model`. See §5 of the configuration contracts.
"""

REF_KEY = "$ref"
"""Import path of an object that replaces the node without being called.

For example `$ref: torch.float32`.
"""

PARTIAL_KEY = "$partial"
"""Flag that builds a `functools.partial` instead of calling the class.

For example `$partial: true`.
"""
