# Validation

`validate` checks a loaded config against the schemas of its classes. It calls no
configured class, but it imports the modules that `$class` and `$ref` name and runs
resolvers, so validate only configs you trust. `instantiate` runs the same check
before it builds, so a config error never leaves objects partly built.

## Load, validate, instantiate

`load_config` assembles the full config (imports, bases, defaults, overrides)
without checking schemas. `validate` checks it, and `instantiate` builds the
objects:

```{literalinclude} ../examples/editor/editor_app.py
:language: python
:caption: editor_app.py
```

```{literalinclude} ../examples/editor/main.py
:language: python
:caption: main.py
```

`AppConfig` describes the root of the file. A plain value is typed as usual, and a
child that is instantiated later is typed as the class it builds, such as
`model: Model`. The node under `training.model` must then name `Model` or a
subclass in `$class`, and it is checked against `ModelConfig`, the schema of
`Model`.

`validate` returns nothing and raises `ConfigValidationError` at the first problem,
with the key path of the node. To test a config without handling the error
elsewhere, catch it:

```python
try:
    validate(config, schema=AppConfig)
except ConfigValidationError as error:
    print(f"invalid config: {error}")
```

## Fragments and library files

A file that others import is often incomplete on purpose: it leaves `???` slots and
refers to keys that its consumers define.

```{literalinclude} ../examples/validation/encoder.yaml
:language: yaml
:caption: encoder.yaml
```

```{literalinclude} ../examples/validation/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/validation/models.py
:language: python
:caption: models.py
```

```{literalinclude} ../examples/validation/main.py
:language: python
:caption: main.py
```

- `allow_missing=True` accepts missing values: `???`, required fields that are not
  given, and interpolations to missing or unknown keys. Every value that is given is
  still checked.
- `schema` names the class the root must match. A dataclass checks the root as a
  section. Another class, such as `Encoder`, checks a root with `$class` as a node
  that builds it, and a root without `$class` against the class's schema.

## What is checked

- Every node with `$class`, against the schema of its class, children before
  parents. Classes are imported to find their schemas, but not called.
- Unknown keys, invalid plain values and missing required fields.
- Unresolved values: a `???` or a failing interpolation makes the config invalid,
  unless `allow_missing`.
- Object fields: the `$class` of the node must be the annotated class or a
  subclass. The check is skipped when `$class` names a function, and for
  `$partial: true` nodes.
- Classes and `$ref` targets that cannot be imported.

What `from_config` makes of a valid config is not checked. Plain values are
checked the way `instantiate` coerces them, so `batch_size: "64"` is valid for an
`int` field. The config itself is not changed.

To check files from a terminal, a pre-commit hook or CI, use
[`omegakit check`](command-line.md), on trusted branches only.
