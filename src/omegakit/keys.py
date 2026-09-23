META_KEY = "$meta"
"""Arbitrary metadata attached to any node, e.g. `$meta: {author: myname}`.

Preserved on load only when `load_config(..., keep_meta=True)`, and always ignored by
`instantiate` (never passed to a constructor).
"""

IMPORT_KEY = "~import"
"""String value replacing a node with another config file, `~import <path>[#<node>]`.

A relative path is resolved against the importing file, an absolute path is used as-is;
the optional `#<node>` selects a subnode of the imported config (e.g. `~import
models/base.yaml#optimizer`). Circular imports raise a `ValueError`.

The statement may contain `${...}` interpolations (e.g. `~import
${paths:config_dir}/models/base.yaml`). Being part of the reference itself, they are
resolved eagerly at assembly time — per file, before any `$base` merge — so resolvers
are always available, but config-value references only see keys literally present in
the importing file at that point.
"""

BASE_KEY = "$base"
"""Defaults merged into the current node, e.g. `$base: {lr: 0.1, steps: 100}`.

The `$base` mapping is merged underneath the node (the node's own keys win) before
instantiation. Bases are merged bottom-up, so nested nodes resolve their own `$base`
first. Typically populated via `~import` or an interpolation (`$base: ${..._common}`).

Resolution contract: assembly (`~import` + `$base` merge) is structural and resolves
nothing except the `$base`/`~import` reference itself (it decides what to merge).
Every `${...}` interpolation and `???` mandatory-missing value is carried through
untouched and resolved once, later — lazily on access, or when `instantiate` builds the
object tree — against the fully-assembled config. So a `???` means "a `$base` consumer
must supply this key"; unfilled, it errors at use time (naming the key), never during
assembly.
"""

DEFAULTS_KEY = "$defaults"
"""Defaults merged underneath every dict-valued sibling of the containing mapping.

Scalar and list-valued siblings and `$`-keys are untouched. Item keys win, and passes
run bottom-up, so an inner `$defaults` wins over an outer one.

Follows the `$base` resolution contract: only the `$defaults` reference itself is
resolved eagerly; every `${...}` inside the values is carried through and resolved
lazily at the item's final position — relative interpolations (`${.id}`) are written
as-if already inside an item, absolute ones resolve from the config root.
"""

CLASS_KEY = "$class"
"""Import path of the class to build from a node, e.g. `$class: myapp.models.Foo`.

Its presence marks a node as instantiable: `instantiate` imports the class and calls it
(or its `from_config`) with the node's other keys as keyword arguments.
"""

REF_KEY = "$ref"
"""Import path resolved to the referenced object itself, e.g. `$ref: torch.float32`.

Unlike `$class` the object is imported but not called. A `$ref` node must contain no
other keys (`$meta` aside).
"""

PARTIAL_KEY = "$partial"
"""Flag deferring instantiation of a `$class` node, e.g. `$partial: true`.

When true, `instantiate` returns a `functools.partial` bound to the resolved arguments
instead of the constructed object, so remaining arguments can be supplied at call time.
"""
