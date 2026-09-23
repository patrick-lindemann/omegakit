# Configuration contracts

This page is the normative description of the omegakit configuration language. Code,
tests and the README follow it. A change to the language changes this page in the
same commit.

## 1. Pipeline order

`load_config` assembles a file in this order:

1. Parse the YAML file.
2. Resolve `~import` depth-first. Each imported file resolves its own imports before
   it is inserted. No `$base` is merged during this step.
3. Merge `$base`, children before parents.
4. Apply `$defaults`, children before parents.
5. Merge the overrides.
6. Strip `$meta` (unless `keep_meta=True`) and the construction keys `$class`,
   `$ref` and `$partial` (if `keep_targets=False`).

Consequences:

- `$base: ~import file.yaml` works, because the import has already replaced the
  string when bases are merged.
- A `$defaults` delivered by a `$base` or an `~import` works, because defaults are
  applied after all bases are merged.
- Overrides cannot introduce `~import`, `$base` or `$defaults`. They arrive after
  assembly, so these keys and values stay literal.
- `$meta` and construction keys introduced by overrides are stripped like any
  other.

## 2. Precedence

From strongest to weakest:

1. Overrides.
2. The node's own keys.
3. Later items of a list-valued `$base`.
4. Earlier items of a list-valued `$base`.

`$defaults` is weaker than the item it is applied to. Because `$defaults` is
applied children before parents, an inner `$defaults` has already been merged into
an item when an outer `$defaults` is merged underneath it, so the inner one wins.

`$defaults` applies only to the dict-valued siblings in its own mapping. Scalars,
lists and `$`-prefixed siblings are untouched, and grandchildren are reached only
through the merged sibling's own keys.

## 3. Resolution timing

Only structural references are resolved during assembly:

- the path of an `~import`, including `${…}` inside it
- the value of `$base`
- the value of `$defaults`

An `~import` path is resolved against its own file as parsed: it sees resolvers
and the keys literally present in that file. It does not see keys contributed by a
`$base`, by another file, or by overrides.

A `$base` or `$defaults` value that is an interpolation (`$base: ${_common}`) sees
the referenced node as assembled so far. Nodes are visited in document order,
children before parents.

**Known limitation (finding 15, fix deferred):** if the referenced node comes
later in document order and has its own `$base`, it has not been merged yet. In
`{m: {$base: ${c}}, c: {$base: {a: 1}, b: 2}}`, `m` ends up with a literal `$base`
key: `{$base: {a: 1}, b: 2}`. If `c` comes first, `m` gets `{b: 2, a: 1}`. Until
this is fixed, reference only nodes that come earlier, or nodes without their own
`$base`.

Every other `${…}` stays an interpolation until it is accessed or instantiated, and
then resolves against the assembled config. This includes interpolations inside
imported files and inside `$base` and `$defaults` values. A relative interpolation
such as `${.id}` resolves at the node's final position.

`instantiate` and `prepare` resolve a copy. They never mutate the config passed in.

## 4. `???` lifecycle

- A `???` value survives `load_config`.
- A consumer of the `$base` that carries it, or an override, can fill it.
- If it is still missing, accessing it raises `MissingMandatoryValue`, and so does
  instantiating any node that contains it. The error names the full key.

## 5. Instantiation

- A mapping with `$class` is instantiable. `$class` is a dotted import path
  `module.attribute`; the attribute is imported and called.
- If the imported object has a `from_config` attribute, `from_config(arguments)` is
  called instead of the object. This is duck-typed: `Configurable` is one
  implementation, not a requirement. `arguments` is a plain `dict` of the
  materialized arguments.
- Nested instantiable nodes, in mappings and lists, are built before their parent,
  and the parent receives the built objects.
- `$meta` is never passed to a constructor or to `from_config`.
- A mapping with `$ref` is replaced by the imported object, without calling it.
  `$ref` allows no sibling keys except `$meta`. A top-level `$ref` is not
  instantiable: `instantiate` requires `$class` at the top.
- `$partial: true` returns a `functools.partial` of the class (or of its
  `from_config`) with the materialized arguments. Nested objects are still built
  immediately.
- `prepare(config)` is `instantiate` with the top-level call deferred. Nested nodes
  are built during `prepare`, and nested `$partial` nodes stay partials.
- Call-time keyword arguments to a partial from `prepare` or `$partial`:
  - For a class without `from_config`, they reach the constructor, and a call-time
    value wins over a config value of the same name.
  - For a class with `from_config`, they reach `from_config` as `**kwargs`. The
    arguments mapping stays the first positional argument.
  - The default `Configurable.from_config` forwards `**kwargs` to the constructor,
    calling `cls(**dict(config, **kwargs))`, so a call-time value wins as it does for
    plain classes.
- `$partial: true` makes a node partial, and `$partial: false` does not. Any other
  value, including the string `"true"` and `1`, raises `ValueError`.
- A raw `dict` is resolved exactly like a `DictConfig`: `${…}` is resolved, and
  `???` raises `MissingMandatoryValue`. It is converted with `OmegaConf.create`, so
  its values must be types OmegaConf supports. A value such as an arbitrary Python
  object raises `UnsupportedValueType`.
- Errors from a constructor or `from_config`:
  - Any `Exception` raised by the call propagates unchanged, with the same type,
    arguments and traceback.
  - It gets one note, `while instantiating <path> (<class>)`. `<path>` is the
    dotted key path of the failing node from the config passed to `instantiate`,
    with list indices as segments (`items.0.model`), or `<root>` for the top node.
    `<class>` is the `$class` value.
  - A partial from `prepare` or `$partial` is called outside omegakit, so its errors
    get no note.

## 6. Key namespace

- Every key that starts with `$` is reserved for omegakit. The defined keys are
  `$class`, `$ref`, `$partial`, `$meta`, `$base` and `$defaults`.
- `~import` is a value prefix, not a key. Only a string value that starts with
  `~import` is an import. Elsewhere in a string it is literal text.
- `load_config` keeps unknown `$` keys untouched.
- When instantiating, any mapping with a `$` key that is not allowed there raises
  `ValueError`. A `$class` node allows `$meta` and `$partial`, a `$ref` node allows
  `$meta`, and a plain mapping allows only `$meta`. In particular, `$class` and
  `$ref` cannot be combined.

## 7. Import semantics

- The syntax is `~import <path>[#<node>]`. Whitespace before `<path>`, after the
  statement and around `<node>` is ignored. Whitespace before `#` is part of the
  path.
- A relative path is resolved against the directory of the importing file. An
  absolute path is used as is.
- `<node>` is a dot-separated path from the root of the imported file. A segment
  selects a key in a mapping or an integer index in a list (`#a.b.0`). A negative
  index counts from the end (`#a.b.-1`). An empty `<node>` selects the whole file.
- An import can replace a mapping value or a list item. The imported file may be a
  mapping or a list.
- Cycles are detected per import chain: a file that imports itself, directly or
  through other files, raises `ValueError`. Importing the same file from two
  branches (a diamond) is not a cycle.
- Every import produces an independent copy. Changing one imported node never
  changes another import of the same file or node.
- Each imported file is read once per `load_config` call.
- A statement with more than one `#` raises `ValueError`. File names containing
  `#` cannot be imported.
- A `<node>` segment that walks through a scalar, a non-integer segment on a list,
  or an out-of-range index raises the same `ValueError` as a missing node.

## 8. Error model

| Misuse | Exception | Message contains |
|---|---|---|
| Circular `~import` | `ValueError` | `Circular import detected` and the path |
| `~import` of a missing file | `FileNotFoundError` | the resolved path |
| `~import` of a missing node | `ValueError` | `selects node`, the node and the file |
| `~import` selector through a scalar, or a bad or out-of-range list index | `ValueError` | as missing node |
| `~import` with more than one `#` | `ValueError` | `more than one` `#` |
| `~import` path with an unknown interpolation key | `InterpolationKeyError` | the key |
| `$base` not a mapping or list of mappings | `ValueError` | `$base` |
| `$defaults` not a mapping | `ValueError` | `$defaults` |
| Overrides of another type than `DictConfig`, `dict` or `list` | `ValueError` | `Unsupported overrides type` |
| `instantiate`/`prepare` on a node without `$class` | `ValueError` | `Cannot instantiate config with no` `$class` |
| `$class`/`$ref` module not found | `ModuleNotFoundError` | the module |
| `$class`/`$ref` attribute not found | `ImportError` | `Could not import`, attribute and module |
| `$ref` with sibling keys other than `$meta` | `ValueError` | `cannot contain any other keys` |
| Raw dict value that OmegaConf does not support | `UnsupportedValueType` | the key |
| Unknown `$` key, or `$class` with `$ref`, at instantiation | `ValueError` | the key and `reserved` |
| `$partial` not a boolean | `ValueError` | `$partial` |
| `???` accessed or instantiated | `MissingMandatoryValue` | the full key |
| Unresolvable `${…}` accessed or instantiated | `InterpolationKeyError` (or another OmegaConf error) | the key |
| Exception from a constructor or `from_config` | unchanged | original message, plus the note from §5 |
| Resolver registered twice without `replace=True` | `ValueError` | `already registered` |
| Torch resolver without PyTorch installed | `ImportError` | `require PyTorch` |

A malformed dotlist override such as `["a"]` is not an error: OmegaConf sets `a` to
`None`.

## 9. Environment

- Importing `omegakit` or any of its modules has no side effects: no resolver is
  registered, and `torch` is not imported.
- Resolvers are opt-in. Registration is global to OmegaConf, and an existing name
  raises unless `replace=True` is passed. `omegakit.resolvers` exports nothing:
  each resolver is imported from its own module, which carries its own
  dependencies.
- omegakit does not load `.env` files.
- OmegaConf is pinned to 2.3.x, because assembly uses private OmegaConf node APIs.
- Configs import and call arbitrary Python objects. Load them only from trusted
  sources.
