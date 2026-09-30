# Dataclass schemas

A plain dataclass describes a config: which keys it has, and what each one holds.
omegakit checks a config against it before anything is built, and builds a typed
result from it:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: from enum import
```

```{code-block} text
:caption: Output

experiment.run_dir: PosixPath('runs/linear')
experiment.data: Data(n=256, noise=0.1)
experiment.model: Linear(in_features=1, out_features=1, bias=True)
experiment.epochs: 100
```

`Experiment` has three of the four field kinds that the table under Rules lists.
`seed`, `run_dir` and `epochs` are values, converted and checked, so `run_dir` is a
`Path`, and `epochs` took its default. `data` is a section, a plain mapping built
into `Data`. `model` is an object, a `$class` node
([Instantiation](../../objects/instantiation/index.md)).

A class that is not a dataclass, such as a PyTorch module, can carry a schema too,
through [`Configurable`](../../objects/configurable-classes/index.md).

## Rules

**Which schema a node has.** It is found from the node's `$class`, or from
`schema` for a root without `$class`:

- A dataclass is its own schema.
- A `Configurable` has its `schema`
  ([Configurable classes](../../objects/configurable-classes/index.md#rules)).
- Any other class or function has none, and so has a `Configurable` without a
  `schema`. Its arguments are not checked, but the `$class` nodes inside them are.

**Field kinds.**

| Annotation | Config value | Checked by | The result holds |
|---|---|---|---|
| **data**: every annotation that OmegaConf accepts, such as `int`, `str`, `Path`, enums, `Literal`, dataclasses of these, and `list`, `dict`, `tuple` and unions of these, optional or not | plain values | OmegaConf | the value as OmegaConf converts it |
| **object**: a class that OmegaConf does not accept, a union of such classes, a `list` or `dict` of them, optional or not, also through a `type` alias | a `$class` or `$ref` node, a list or mapping of them, or `null` if optional | the class check ([Validation](../validation/index.md#rules)), then the node's own schema | the built object |
| **`Any`** | anything | not checked, but `$class` nodes inside are | the value, with `$class` nodes built |

- A data field accepts, converts and rejects values as OmegaConf's
  [structured configs](https://omegaconf.readthedocs.io/en/latest/structured_config.html)
  do. Enums, for example, take a member name or a value:

```{literalinclude} main.py
:language: python
:caption: main.py (enums)
:start-at: from enum import
```

```{code-block} text
:caption: Output

loss 'MAE': Loss.MAE
loss 'mean absolute error': Loss.MAE
```

- OmegaConf builds the dataclasses inside data fields. A dataclass default of a
  dataclass that the config gives is built again from its values, so its
  `__post_init__` runs again, as in `OmegaConf.to_object`.
- `init=False` fields and `InitVar`s are not configurable: a key for them is
  unknown.
- Items of an object `list` or `dict` are `$class` or `$ref` nodes, or plain
  mappings when the item type is a dataclass (a section).
- An absent field takes its dataclass default. A field without one is required.
  Schema defaults win over constructor defaults.
- A dataclass may contain itself, directly or through others, as OmegaConf allows.

**Unsupported.** An annotation that OmegaConf rejects and that is not built from
classes, such as `set[int]`, `Sequence[int]` or `int | Encoder`, raises
`SchemaDefinitionError` with OmegaConf's reason, and so does an annotation that
does not resolve, such as a name imported under `TYPE_CHECKING`. Both are raised
wherever the class is reached: in a `$class` or a `schema` that `validate` or
`instantiate` checks.

**Checking a node.** `validate` checks every node that has a schema, and
`instantiate` and `prepare` do before they build:

1. Check each object and `Any` field, children first
   ([Validation](../validation/index.md#rules)). A plain mapping in a
   field annotated with a dataclass is a section, checked the same way.
2. Check the node's own keys and values with one OmegaConf merge. An unknown key,
   a missing required field and a wrong value raise `ConfigValidationError` with
   OmegaConf's message, naming the path and the schema class; a wrong value inside
   a dataclass in a list is named by its own field, as OmegaConf reports it. Object
   and `Any` values never enter OmegaConf.

The config is not changed. A dataclass named by `$class` is then called with the
converted fields ([Instantiation](../../objects/instantiation/index.md#rules)).
