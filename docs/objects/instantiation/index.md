# Instantiation

`instantiate` builds Python objects from a config node. `$class` calls a class or
function, `$ref` imports an object without calling it, and `$partial` defers a call:

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

experiment.model: Linear(in_features=16, out_features=1, bias=True)
experiment.loss: mse_loss
optimizer: SGD
lr: 0.1
lr: 0.01
make_model(out_features=3): Linear(in_features=16, out_features=3, bias=True)
error: `$class: subprocess.Popen` in `model` names a module that is not in `allowed_modules`.
```

## `$class`

`$class: torch.nn.Linear` names the class to build, and the node's other keys became
its arguments. The root of `experiment.yaml` has no `$class`, so
`schema=Experiment` says what to build it as, and the result is typed as an
`Experiment` for your editor and type checker. How `Experiment` checks the config
is on [Dataclass schemas](../../schemas/dataclass-schemas/index.md).

## `$ref`

`$ref: torch.nn.functional.mse_loss` gave the function itself, uncalled.

## `$partial` and `prepare`

The optimizer needs the model's parameters, which exist only once the model is
built. `$partial: true` gave a `functools.partial` of `torch.optim.SGD`, which the
code called with them. Arguments passed to the partial win over the config's, as
`lr=0.01` did. `prepare(config.model)` gave a partial of the model node itself,
which built a `Linear` with three outputs.

## Checking before building

`instantiate` and `prepare` check the node as [`validate`](../../schemas/validation/index.md)
does before they build anything. `allowed_modules` limits `$class` and `$ref` to the
parts of PyTorch the config uses: the override swapped in `subprocess.Popen`, and
the module was never imported
([Restricting imports](../../security/restricting-imports/index.md)).

## Rules

**Building.**

- A mapping with `$class` is built. `$class` is a dotted path `module.attribute`;
  the attribute is imported and called with the node's other keys as keyword
  arguments.
- `instantiate` and `prepare` first merge `overrides`
  ([Overrides](../../guide/overrides/index.md#rules)), resolve the node and validate it as
  `validate` does ([Validation](../../schemas/validation/index.md#rules)), with the same
  `schema` and `allowed_modules`, and only then build. An invalid override raises
  `ConfigLoadError`. A config error, a `???`, a failing
  interpolation and an exception from a resolver all raise `ConfigValidationError`
  before any configured class is called. OmegaConf's error is the `__cause__`, and
  the message names the full key. A class that cannot serve as a schema raises
  `SchemaDefinitionError`.
- A target with a `from_config` attribute is built with `from_config(arguments)`
  instead. The lookup is by name, so any class with that classmethod works,
  `Configurable` or not. `arguments` is a `dict` of the built arguments, or the
  typed config when the class is a `Configurable` with a schema
  ([Configurable classes](../configurable-classes/index.md)).
- A dataclass target is its own schema: its arguments are checked and converted
  against its fields before it is called
  ([Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules)).
- Nested `$class` nodes, in mappings and lists, are built before their parent,
  which receives the objects.
- A `dict` passed in is converted with `OmegaConf.create` and treated like a
  `DictConfig`. A value OmegaConf does not support raises `UnsupportedValueType`.
- An exception from a constructor or `from_config` propagates unchanged in type,
  arguments and traceback, with one note, `while instantiating <path> (<class>)`.
  `<path>` is the dotted path from the node passed in, such as `items.0.model`, or
  `<root>`, and `<class>` the `$class` value. An error from calling a partial
  later gets no note.

**The root and `schema`.**

- Without `schema`, the node passed to `instantiate` or `prepare` must have
  `$class`, or they raise `ConfigValidationError`.
- With `schema`, a root with `$class` must name `schema` or a subclass, checked as
  `validate(config, schema=...)` checks it. A root without `$class` is built as if
  its `$class` named `schema`: a dataclass gives an instance of itself, and a
  `Configurable` is built through `from_config`. A class without a dataclass schema
  raises `ConfigValidationError`, and anything that is not a class raises
  `TypeError`.
- A root with `$ref` raises `ConfigValidationError`, with or without `schema`.
- The result is typed as `schema`, or as a `functools.partial` of it from
  `prepare`, and as `Any` without `schema`.

**References.** A mapping with `$ref` is replaced by the imported object, uncalled.
It allows no other key except `$meta`; another key raises `ConfigValidationError`.

**Partials.**

- `$partial: true` gives a `functools.partial` of the class, or of its
  `from_config`, with the built arguments. Nested objects are still built right
  away. `$partial: false` builds normally. Any other value, including `"true"` and
  `1`, raises `ConfigValidationError`.
- `prepare(node)` is `instantiate` with the call of `node` itself deferred. Nested
  nodes are built during `prepare`, and nested `$partial` nodes stay partials.
- Keyword arguments given when calling a partial win over the config's. Without
  `from_config` they reach the constructor. With `from_config` they arrive as its
  `**kwargs`, after the arguments. The default `Configurable.from_config` calls
  `cls(**{**fields, **kwargs})`, where `fields` are the typed config's fields, or
  the arguments when there is no schema.



**Reserved keys.**

- Every key that starts with `$` is reserved. The [API](../../api/index.md#special-keys)
  lists the defined ones. `~import` is a value prefix, not a key.
- `load_config` keeps unknown `$` keys. Validating or building rejects a `$` key
  where it is not allowed, with `ConfigValidationError`: a `$class` node allows
  `$meta` and `$partial`, and a `$ref` node or a plain mapping allows only
  `$meta`. `$class` and `$ref` cannot be combined.
