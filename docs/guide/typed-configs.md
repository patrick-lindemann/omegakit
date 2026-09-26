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

```{literalinclude} ../examples/default-from-config/main.py
:language: python
```

`check_schema` also runs automatically, once per class, before a node's children are
built. Call it in a test to catch a mismatch without a config.

## Field kinds

Each schema field is one of three kinds:

- **Native** fields hold plain values: `int`, `float`, `bool`, `str`, `bytes`,
  `Path`, `Enum`, `Literal`, `TypedDict`, dataclasses of these, and `list`, `dict`,
  `tuple`, `Sequence` or `Mapping` of these, and unions of these. OmegaConf
  validates and coerces them, and omegakit adds what OmegaConf 2.3 lacks, so every
  supported OmegaConf version behaves the same.
- **Object** fields are typed by the class they build, such as
  `encoder: Encoder | None`, or a `list` or `dict` of it. In YAML they hold a
  `$class` node whose class is `Encoder` or a subclass, or a `$ref` to an
  `Encoder`. A dataclass with object fields is a section: a plain mapping in it is
  built as that dataclass.
- **`Any`** fields are not validated. Use them for values that OmegaConf cannot
  hold, such as objects returned by resolvers.

```{literalinclude} ../examples/field-types/models.py
:language: python
:caption: models.py
```

```{literalinclude} ../examples/field-types/model.yaml
:language: yaml
:caption: model.yaml
```

```{literalinclude} ../examples/field-types/main.py
:language: python
:caption: main.py
```

- Enums are written by member **name** or **value** (`gelu` or `GELU`); a name wins
  over an equal value of another member.
- A union may hold one mapping type and one list type. A mapping or a list is
  coerced like that member; a scalar must match a member's type exactly.
- Tuples come from YAML lists; `tuple[int, int]` needs exactly two items.
- `init=False` fields are computed by the dataclass, and a config cannot set them.
  An `InitVar` needs a default and cannot be set either.

## A custom `from_config`

A custom `from_config` receives the typed config, with object fields already built,
and calls the constructor itself. Pyright checks that call. Children chosen by code
rather than by the user are created with `make_node`:

```{literalinclude} ../examples/typed-model/main.py
:language: python
```

`kind` is an input choice in the YAML file, so overrides such as `model.kind=A` work.
`encoder` is an object field, so users configure it. `A` and `B` are created by
`make_node` inside `from_config`; users cannot reach them.

## Factories

A `from_config` that returns an instance of a subclass must annotate the base class
as its return type. `-> Self` with a subclass return is a pyright error:

```{literalinclude} ../examples/factory/main.py
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

```{literalinclude} ../examples/escape-hatches/main.py
:language: python
```

## Supported dataclasses

The lookup raises `ConfigValidationError`, naming the field and the fix, for
`InitVar` fields without a default; for `set` and the other abstract containers; for
containers that mix plain values and objects; for unions that mix plain values and
classes, or that hold two mapping or two list types; and for annotations that cannot
be resolved at runtime, such as names imported under `TYPE_CHECKING`.
