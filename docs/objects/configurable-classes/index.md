# Configurable classes

A class can name the schema of its config: subclass `Configurable` and pass a
`TypedDict` as the class keyword `schema`. omegakit then checks the keys of every
`$target` node that names the class, before anything is built. Use it for a class
that is no dataclass, such as a PyTorch module:

```{literalinclude} models.py
:language: python
:caption: models.py
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: make_mlp =
```

```{code-block} text
:caption: Output

model: MLP(
  (0): Linear(in_features=1, out_features=8, bias=True)
  (1): ReLU()
  (2): Linear(in_features=8, out_features=1, bias=True)
)
ConfigSchemaError: `hiden` is not a field of `MLPConfig`. Its fields are `hidden`, `layers`, `activation`. (at the root)
node: {'$target': 'models.MLP', 'hidden': 4, 'layers': 2}
```

The config was checked against `MLPConfig` before `MLP` was called, so
`hidden: "8"` arrived as the integer 8, and the misspelt `hiden` was rejected. The
keys and how they are checked are as for any
[TypedDict schema](../../schemas/typed-dict-schemas/index.md). `MLPConfig` has no
defaults: `layers` and `activation` are `NotRequired`, and `MLP.__init__` keeps
their defaults.

`make_node` gave the node that builds an `MLP`, for code that picks a class itself,
such as a test or a `from_config` ([Instantiation](../instantiation/index.md#rules)).

## `from_config`

omegakit builds a `Configurable` through its class method `from_config(config,
**kwargs)`. `config` is a `dict` of the checked, converted values, with the keys
that the config gives, and with the objects of nested `$target` nodes already
built. The default calls `cls(**{**config, **kwargs})`. Override it when the config
and the constructor differ, for example when a key names the subclass to build.
Annotate `config` with the schema, as in `config: MLPConfig`, and your type checker
knows its keys. Keep `**kwargs` in the signature, where the arguments of a partial
arrive.

## Partials

A partial may leave required keys open until it is called:

```{literalinclude} main.py
:language: python
:caption: main.py
:start-at: make_mlp =
```

```{code-block} text
:caption: Output

make_mlp(hidden=2): Linear(in_features=1, out_features=2, bias=True)
ConfigSchemaError: `MLPConfig` requires `hidden`. (at the root)
```

The keys of `MLPConfig` that the call gives join the config's, and a required key
that is still open raises when the partial is called.

## Rules

- A subclass of `Configurable` names its schema in the class keyword `schema`, a
  `TypedDict`, as in `class MLP(nn.Sequential, Configurable, schema=MLPConfig)`.
  Anything else, also a dataclass, raises `SchemaDefinitionError` when the class is
  defined, and a misspelt keyword raises `TypeError` there; type checkers report
  both. A subclass inherits the schema, and `schema=None` removes it. A `schema`
  attribute in the class body is no schema.
- `Configurable` takes no class keyword but `schema`. A base class that takes class
  keywords of its own comes before it, as in
  `class MLP(Registered, Configurable, name="mlp", schema=MLPConfig)`, and passes
  `schema` on.
- A `$target` node of a class with a schema is checked against it
  ([TypedDict schemas](../../schemas/typed-dict-schemas/index.md#rules)): an
  unknown key and a missing required key raise `ConfigSchemaError`, and every
  value is checked and converted by its annotation. A class without a schema has
  its arguments unchecked, except for the `$target` nodes inside them. A
  `Configurable` that is a dataclass and has no schema is checked against its
  fields ([Dataclass targets](../../schemas/typed-dict-schemas/index.md#dataclass-targets)),
  so a dataclass whose `from_config` takes other keys than its fields names them in
  a schema.
- Any class with a `from_config`, `Configurable` or not, is built with
  `from_config(config)`, where `config` is a `dict` of the values that the config
  gives, checked and converted. No instance of the schema is built. What
  `from_config` returns is checked only against the second argument of
  `instantiate` ([Instantiation](../instantiation/index.md#rules)).
- A class with `from_config` takes its arguments by name: `$args` raises
  ``ConfigTargetError: `models.MLP` takes its arguments by name, so it cannot take
  `$args`.``
- A partial of a class with `from_config`, from `$partial: true` or `prepare`,
  calls `from_config` when it is called, with the call's keyword arguments as
  `**kwargs`. For a `Configurable` with a schema, the keys of the schema that the
  call gives are added to `config` instead, and a required key that neither gives
  raises `ConfigSchemaError` at the call. An error from calling a partial gets no
  note.
