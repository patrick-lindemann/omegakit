# Dataclass schemas

A plain dataclass describes a config: which keys it has, and what each one holds.
omegakit checks a config against it before anything is built, and builds a typed
result from it. `curvefit` describes a whole experiment with two dataclasses:

```{literalinclude} ../../curvefit/curvefit/__init__.py
:language: python
:caption: curvefit/__init__.py (excerpt)
:start-at: "@dataclass"
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: class Loss
```

```text
Splits Synthetic
Polynomial ('runs', 'poly3-adam', 'seed0')
5
```

The root of the experiment file has no `$class`, so `schema=Experiment` says what it
is. A dataclass named by `$class` is its own schema too: `curvefit`'s models and
datasets are plain dataclasses, so `degree: "4"` became the integer 4.

## Field kinds

`Experiment` shows the kinds of field:

- **Values:** `name: str`, `seed: int` and `run_dir: Path`. The config holds plain
  values, which are converted and checked, so `run_dir` is a `Path`.
- **Sections:** `data: Splits`. A field annotated with a dataclass holds a plain
  mapping, checked against that dataclass and built into it.
- **Objects:** `model: Model`, `trainer: Trainer` and the others. The config holds a
  `$class` node of that class or a subclass, or a `$ref` to an instance, and the
  result holds the built object. `optimizer` is a partial, and `metrics` holds
  functions ([Instantiation](../../objects/instantiation/index.md)).
- **`Any`:** the value is not checked, but `$class` nodes and reserved keys inside
  it are.

A field without a default is required. `tracker` has the default `None`, so an
experiment may leave it out.

A class can also carry a schema that differs from its constructor, through
[`Configurable`](../../objects/schemas/index.md).

## Rules

**Which schema a node has.** It is found from the node's `$class`, or from
`schema` for a root without `$class`:

- A dataclass is its own schema.
- A class that subclasses `Configurable[TConfig]` with a dataclass `TConfig` has
  `TConfig` ([Configurable classes](../../objects/schemas/index.md#rules)).
- Any other class or function has none, including a bare `Configurable` and one
  with a `TypedDict` or `Mapping` `TConfig`. Its arguments are not checked, but the
  `$class` nodes inside them are.

**Field kinds.**

| Annotation | Config value | Checked by | The result holds |
|---|---|---|---|
| **native**: `int`, `float`, `bool`, `str`, `bytes`, `Path`, `Enum`, `Literal` of `str`, `int` or `bool`, `TypedDict`, dataclasses whose fields are all native, `list`, `dict`, `tuple`, `Sequence` and `Mapping` of these, and unions of these, optional or not | plain values | OmegaConf, then omegakit | the converted value |
| **object**: any other class, generic classes, unions of classes, `list` or `dict` of these, optional or not, also through a `type` alias | a `$class` or `$ref` node, a list or mapping of them, or `null` if optional | the class check ([Validation](../../objects/validation/index.md#rules)), then the node's own schema | the built object |
| **`Any`** | anything | not checked, but `$class` nodes inside are | the value, with `$class` nodes built |

- Behaviour does not depend on the OmegaConf version.
- Enums accept a member name or value, as in the example below. A name wins over
  an equal value of another member, and a value needs the exact type of the
  member's value.
- A `Literal` value is converted like its type, then compared by type and value:
  `"2"` is valid for `Literal[1, 2]`, `true` is not.
- A union has at most one mapping member (dataclass, `dict`, `Mapping`,
  `TypedDict`) and one list member (`list`, `tuple`, `Sequence`). A mapping or a
  list is checked, with conversion, as that member. A scalar must match a scalar
  member's type exactly: `"5"` is not an `int`, `True` is not an `int`, `3` is not
  a `float`, and a string is not a `Path` or an enum. `null` needs `None` in the
  union.
- Tuples come from lists, and `tuple[A, B]` needs exactly two items. `Sequence`
  and `Mapping` give a `list` and a `dict`. A `TypedDict` field is an unchecked
  `dict`.
- `init=False` fields and `InitVar`s are not configurable: a key for them is
  unknown. An `InitVar` needs a default.
- Items of an object `list` or `dict` are `$class` or `$ref` nodes, or plain
  mappings when the item type is a dataclass (a section).
- A field annotated with a dataclass whose fields are all values takes only a
  plain mapping. A `$class` node there raises `ConfigValidationError`.
- An absent field takes its dataclass default. A field without one is required.
  Schema defaults win over constructor defaults.

```{literalinclude} main.py
:language: python
:caption: main.py (enums)
:start-at: class Loss
```

```text
Loss.MAE
Loss.MAE
```


**Unsupported**, raising `ConfigValidationError` that names the field and the fix:
an `InitVar` without a default; `set`, `frozenset` and other abstract containers;
a container that mixes values and objects; a `tuple`, `Sequence` or `Mapping` of
objects; a union that mixes values and classes, or has two mapping or two list
members; `Literal` values other than `str`, `int` and `bool`; an annotation that
`get_type_hints` cannot resolve, such as a name imported under `TYPE_CHECKING`; a
dataclass that contains itself, directly or indirectly (the error names the cycle,
`Tree -> Tree`). A `Configurable` whose schema has a field of its own class is not
recursive: that field holds an object.

**Checking a node.** `validate` checks every node that has a schema, and
`instantiate` and `prepare` do before they build:

1. Check each object and `Any` field, children first
   ([Validation](../../objects/validation/index.md#rules)). A plain mapping in a
   field annotated with a dataclass is a section, checked the same way.
2. Check the node's own keys and values. An unknown key, a missing required field
   and a value that does not convert raise `ConfigValidationError`, naming the path
   and the schema class. Values are checked through OmegaConf and converted into
   the schema's own types. Object and `Any` values never enter OmegaConf.

The config is not changed. A dataclass named by `$class` is then called with the
converted fields ([Instantiation](../../objects/instantiation/index.md#rules)).
