# Instantiation

## Instantiation

- A mapping with `$class` is instantiable. `$class` is a dotted import path
  `module.attribute`; the attribute is imported and called.
- `instantiate` and `prepare` resolve the node (after `overrides`), then validate it
  as `validate` does ([Validation](typed-configs.md#validation)), with the same `allowed_modules`, then build it. A config error therefore raises
  `ConfigValidationError` before any configured target or `from_config` is called. So
  does a resolution error: a `???`, an interpolation that fails, or an exception
  from a resolver, which OmegaConf wraps in `InterpolationResolutionError`.
  OmegaConf's error is the `__cause__`, and the message names the full key.
- If the imported object has a `from_config` attribute, `from_config(arguments)` is
  called instead of the object. This is duck-typed: `Configurable` is one
  implementation, not a requirement. `arguments` is a plain `dict` of the
  materialized arguments, or the typed config when the class has a schema ([Typed configs](typed-configs.md#typed-configs)).
- Nested instantiable nodes, in mappings and lists, are built before their parent,
  and the parent receives the built objects.
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

## References

- A mapping with `$ref` is replaced by the imported object, without calling it.
  `$ref` allows no sibling keys except `$meta`. A top-level `$ref` is not
  instantiable: `instantiate` requires `$class` at the top.

## Partials

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
  - The default `Configurable.from_config` forwards `**kwargs` to the constructor:
    it calls `cls(**{**fields, **kwargs})`, where `fields` are the typed config's
    fields (shallow) or the arguments mapping. A call-time value replaces a field of
    the same name, as it does for plain classes.
- `$partial: true` makes a node partial, and `$partial: false` does not. Any other
  value, including the string `"true"` and `1`, raises `ConfigValidationError`.

## Metadata

- `$meta` is never passed to a constructor or to `from_config`.

## Reserved keys

- Every key that starts with `$` is reserved for omegakit. The defined keys are
  `$class`, `$ref`, `$partial`, `$meta`, `$base` and `$defaults`.
- `~import` is a value prefix, not a key. Only a string value that starts with
  `~import` is an import. Elsewhere in a string it is literal text.
- `load_config` keeps unknown `$` keys untouched.
- When validating or instantiating, any mapping with a `$` key that is not allowed
  there raises `ConfigValidationError`. A `$class` node allows `$meta` and `$partial`, a `$ref` node allows
  `$meta`, and a plain mapping allows only `$meta`. In particular, `$class` and
  `$ref` cannot be combined.
