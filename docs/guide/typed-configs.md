# Typed configs

A config has two halves. The **raw half** is what users write in YAML. The **parsed
half** is what the constructor receives. With typed configs, both are typed:

- A dataclass `TConfig` in `Configurable[TConfig]` is the schema of the raw half. It
  is validated at runtime, with key paths in its errors, and it gives `from_config`
  static attribute types.
- The constructor types the parsed half. Pyright checks a custom `from_config`
  against `__init__`, and `check_schema` checks the default one at runtime.

Classes without a schema keep working exactly as before. The normative rules are in
the [configuration contracts](../contracts.md), section 10.

## A schema with the default `from_config`

The default `from_config` passes every schema field to the constructor. Native
values such as `"64"` are coerced, unknown keys and wrong types raise
`ConfigValidationError`, and `check_schema` verifies that the schema matches
`__init__`:

```{literalinclude} ../examples/default_from_config.py
:language: python
```

`check_schema` also runs automatically, once per class, before a node's children are
built. Call it in a test to catch a mismatch without a config.

## Field kinds

Each schema field is one of three kinds:

- **Native** fields hold plain values: `int`, `float`, `bool`, `str`, `bytes`,
  `Path`, `Enum`, `Literal`, dataclasses of these, and `list` or `dict` of these.
  OmegaConf validates and coerces them, and omegakit checks `Literal` values, such
  as `mode: Literal["train", "eval"]`. Enums are written by member **name**
  (`kind: B`).
- **Object** fields are typed by the class they build, such as
  `encoder: Encoder | None`. In YAML they hold a `$class` or `$ref` node. The built
  object must be an instance of the annotation.
- **`Any`** fields are not validated. Use them for values that OmegaConf cannot
  hold, such as objects returned by resolvers, and for lists of objects.

## A custom `from_config`

A custom `from_config` receives the typed config, with object fields already built,
and calls the constructor itself. Pyright checks that call. Children chosen by code
rather than by the user are created with `make_node`:

```{literalinclude} ../examples/typed_model.py
:language: python
```

`kind` is an input choice in the YAML file, so overrides such as `model.kind=A` work.
`encoder` is an object field, so users configure it. `A` and `B` are created by
`make_node` inside `from_config`; users cannot reach them.

## Factories

A `from_config` that returns an instance of a subclass must annotate the base class
as its return type. `-> Self` with a subclass return is a pyright error:

```{literalinclude} ../examples/factory.py
:language: python
```

## Escape hatches

Nothing is validated in these cases:

- A `TypedDict` `TConfig` types `from_config` statically only. `from_config`
  receives the materialized `dict`, so fields that hold `$class` children must be
  typed as the built object.
- An `Any` field passes its value through.
- Arguments that exist only at runtime, such as `params=model.parameters()`, are not
  schema fields. Pass them to the partial from `prepare`; they reach `from_config`
  through `**kwargs`.

```{literalinclude} ../examples/escape_hatches.py
:language: python
```

## Supported dataclasses

Schemas support a subset of dataclass features. The lookup raises
`ConfigValidationError`, naming the field and the fix, for `init=False`, `InitVar`
and keyword-only fields; for `tuple`, `set` and the abstract containers; for `list`
or `dict` of objects; for unions that mix plain values and classes; and for
annotations that cannot be resolved at runtime, such as names imported under
`TYPE_CHECKING`.
