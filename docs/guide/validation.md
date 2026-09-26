# Validation

`validate` checks a loaded config against the schemas of its classes, without
building anything. Run it after loading to report config errors before any object
is created.

## Load, validate, instantiate

The three steps are separate. `load_config` assembles the full config (imports,
bases, defaults, overrides) without checking schemas, `validate` checks it, and
`instantiate` builds the objects:

```{literalinclude} ../examples/editor/editor_app.py
:language: python
```

```{literalinclude} ../examples/editor/main.py
:language: python
```

`AppConfig` describes the root of the file. A plain value is typed as usual, and a
child that is instantiated later is typed as the class it builds, such as
`model: Model`. The node under `training.model` must then name `Model` or a
subclass in `$class`, and it is checked against `ModelConfig`, the schema of
`Model`.

`validate` returns nothing and raises `ConfigValidationError` at the first problem,
with the key path of the node. `is_valid` runs the same check and returns a
boolean:

```python
if not is_valid(cfg, schema=AppConfig):
    ...
```

Without `schema`, only the nodes with `$class` are checked.

## What is checked

- Every node with `$class`, against the schema of its class, children before
  parents. Classes are imported to find their schemas, but not called.
- Unknown keys, invalid plain values and missing required fields.
- Unresolved values: a `???` or a failing interpolation makes the config invalid,
  so fill them with overrides before validating.
- Object fields: the `$class` of the node must be the annotated class or a
  subclass. The check is skipped when `$class` names a function, and for
  `$partial: true` nodes.

What `from_config` makes of a valid config is not checked. Plain values are
checked the way `instantiate` coerces them, so `batch_size: "64"` is valid for an
`int` field. The config itself is not changed.
