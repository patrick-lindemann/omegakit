# Instantiation

## Instantiation

- A mapping with `$class` is built: `$class` is a dotted path `module.attribute`,
  and the attribute is imported and called with the node's other keys.
- `instantiate` and `prepare` merge `overrides` into a copy, resolve it, validate it
  as `validate` does ([Validation](typed-configs.md#validation)) with the same
  `allowed_modules`, and only then build. Config errors, a `???`, a failing
  interpolation and an exception from a resolver all raise `ConfigValidationError`
  before any configured class is called; OmegaConf's error is the `__cause__`, and
  the message names the full key.
- An object with a `from_config` attribute is built with `from_config(arguments)`
  instead (duck-typed; `Configurable` is one implementation). `arguments` is a
  `dict` of the built arguments, or the typed config if the class has a schema
  ([Typed configs](typed-configs.md#typed-configs)).
- Nested `$class` nodes, in mappings and lists, are built before their parent,
  which receives the objects.
- A `dict` is converted with `OmegaConf.create` and treated like a `DictConfig`;
  values OmegaConf does not support raise `UnsupportedValueType`.
- An exception from a constructor or `from_config` propagates unchanged (type,
  arguments, traceback) with one note, `while instantiating <path> (<class>)`:
  `<path>` is the dotted path from the node passed in (`items.0.model`, or
  `<root>`), `<class>` the `$class` value. Errors from calling a partial later get
  no note.

## References

A mapping with `$ref` is replaced by the imported object, uncalled. It allows no
other key except `$meta`. The node passed to `instantiate` must have `$class`, not
`$ref`.

## Partials

- `$partial: true` gives a `functools.partial` of the class (or its `from_config`)
  with the built arguments; nested objects are still built right away.
  `$partial: false` builds normally, and any other value, including `"true"` and
  `1`, raises `ConfigValidationError`.
- `prepare(node)` is `instantiate` with the call of `node` itself deferred. Nested
  nodes are built during `prepare`; nested `$partial` nodes stay partials.
- Keyword arguments given when calling a partial win over the config's:
  - without `from_config`, they reach the constructor;
  - with `from_config`, they arrive as its `**kwargs`, after the arguments;
  - the default `Configurable.from_config` calls `cls(**{**fields, **kwargs})`,
    with `fields` the typed config's fields (shallow) or the arguments.

## Metadata

`$meta` is never passed to a constructor or to `from_config`.

## Reserved keys

- Every key starting with `$` is reserved. Defined: `$class`, `$ref`, `$partial`,
  `$meta`, `$base`, `$defaults`.
- `~import` is a value prefix, not a key; elsewhere in a string it is literal text.
- `load_config` keeps unknown `$` keys. Validating or building rejects a `$` key
  where it is not allowed, with `ConfigValidationError`: a `$class` node allows
  `$meta` and `$partial`, a `$ref` node and a plain mapping only `$meta`. `$class`
  and `$ref` cannot be combined.
