# TypedDict schemas

A schema is a `TypedDict` that describes a mapping of a config: which keys it has,
and what each one holds. Name it after the values it describes, as in
`ExperimentConfig`. A schema only checks a config; nothing is built from it, and it
has no defaults:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

experiment.yaml: valid
data.noise=high: ConfigSchemaError: The value does not match `DataConfig`: Value 'high' of type 'str' could not be converted to Float (at `data.noise`)
data.size=8: ConfigSchemaError: `size` is not a field of `DataConfig`. Its fields are `n`, `noise`. (at `data`)
model=linear: ConfigSchemaError: Expected `Module`, but the config gives `'linear'`. (at `model`)
```

`ExperimentConfig` has a key of each kind. `seed` and `run_dir` hold **data**,
which OmegaConf converts and checks, so `run_dir` is a valid `Path`. `data` holds a
**mapping**, checked against `DataConfig`, where `noise` may be left out. `model`
holds an **object**, a `$target` node of `nn.Module` or a subclass
([Instantiation](../../objects/instantiation/index.md)). Each override broke one of
them.

## Where a schema applies

- `validate(config, ExperimentConfig)` checks a root without `$target`
  ([Validation](../validation/index.md)).
- `Configurable.schema` checks the keys of every `$target` node of its class
  ([Configurable classes](../../objects/configurable-classes/index.md)).
- A key annotated with a schema, such as `data: DataConfig`, holds a mapping that
  stays a `dict` when it is built, or a `$symbol` to a `dict`, which is checked
  like a mapping of the config.

## Dataclass targets

A dataclass is no schema but a class to build. A `$target` node that names a
dataclass is checked against the dataclass's own fields, by the rules of a schema's
keys, before the dataclass is called:

- Its keys are its init fields. A field without a default, or with OmegaConf's
  `MISSING` as default, is required, and the dataclass applies its own defaults.
- A field with `init=False` is no key. An `InitVar` is no key either, and can be
  given only through `$args`.
- A key annotated with a dataclass holds an object, so it takes a `$target` node of
  that dataclass. A mapping without `$target` raises ``ConfigSchemaError:
  Expected `Data`, but the config gives a mapping. (at `data`)``, and so does
  `validate(config, Data)` for a root without `$target`.

## Rules

**Required keys.** A key is required unless it is `NotRequired`, or its
`TypedDict` has `total=False` and the key is not `Required`. The keys of a base
`TypedDict` keep the rule of their base. A missing required key raises
``ConfigSchemaError: `DataConfig` requires `n`.``, and an unknown key raises
``ConfigSchemaError: `size` is not a field of `DataConfig`. Its fields are `n`,
`noise`.``

**Key kinds.** The annotation of a key decides how it is checked:

- **Data**: an annotation that OmegaConf accepts, such as `int`, `str`, `Path`, an
  enum, a `Literal`, and `list`, `dict`, tuples and optional unions of these.
  OmegaConf converts and checks the value as its
  [structured configs](https://omegaconf.readthedocs.io/en/latest/structured_config.html)
  do, so `"64"` is a valid `int`, and a value that does not fit raises
  ``ConfigSchemaError: The value does not match `DataConfig`: …``, placed at the
  value. A `$target` node in a data key raises `ConfigSchemaError`.
- **Mapping**: a `TypedDict`, also in a union such as `DataConfig | None`. It
  takes a mapping without `$target`, checked against it. In a union of several
  `TypedDict`s, as in `FileConfig | UrlConfig`, the mapping is checked against the
  first one it fits: each of its keys is a field, each required field is given,
  and each `Literal` field, such as a `type` tag, holds one of its values. A
  mapping that fits none raises ``ConfigSchemaError: The mapping fits none of
  `FileConfig`, `UrlConfig`: …``, placed at the mapping.
- **Object**: a class, a union, `list`, `dict` or tuple of classes, `Callable` or
  `Any`. `Any` takes every value; the others are checked by class: a `$target` node must name the class or a
  subclass; a function's result is checked when it returns; a `$partial` node must
  fit `functools.partial`; a `$symbol` is checked with `isinstance`, and for
  `type[X]` it must be a subclass of `X`. An annotation that `isinstance` cannot
  check, such as a `Protocol` that is not runtime-checkable, is not checked.
  Anything else raises ``ConfigSchemaError: Expected `Module`, but the config gives
  `'linear'`.``

**Containers.** The items of a `list` or `dict` are checked by the item
annotation, and the keys of every dictionary are converted by OmegaConf. Each
position of a tuple follows the rule of its own annotation, and a wrong number of
items raises ``ConfigSchemaError: Expected 2 items, but the config gives 1.``

**Recursion.** A schema may contain itself, directly or through other schemas, as
in `children: NotRequired[list[Node]]`.

**Unsupported schemas** raise `SchemaDefinitionError` wherever they are reached:

- a `schema` argument that is no class, and a `Configurable.schema` that is no
  `TypedDict`;
- annotations that cannot be read, such as a name imported only under
  `TYPE_CHECKING`;
- a key that is no Python identifier;
- an annotation of none of the three kinds, such as `set[int]` or `Sequence[int]`;
- a dictionary whose key type OmegaConf does not support, such as `dict[tuple, int]`.
