# Instantiation

`instantiate` builds Python objects from a config. Two keys name Python objects by
their import path: `$target` calls the class or function it names, and `$symbol`
gives the object it names without calling it.

```yaml
activation:
  $target: torch.nn.ReLU    # an instance, ReLU()
activation_class:
  $symbol: torch.nn.ReLU    # the class itself
```

## Building an experiment

The root of `experiment.yaml` names the dataclass `Experiment`, so one call builds
the whole experiment. The other `$target` nodes are built first, and their objects
become its fields:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} experiment.py
:language: python
:caption: experiment.py
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

model: Sequential(
  (0): Linear(in_features=1, out_features=16, bias=True)
  (1): ReLU()
  (2): Linear(in_features=16, out_features=1, bias=True)
)
loss: mse_loss
epochs: 50 batch_size: 32
optimizer: SGD 0.1
optimizer: SGD 0.01
epochs: 5
ConfigTargetError: There is nothing to instantiate: `loss` has no `$target`.
```

`instantiate` checked the config as [`validate`](../../schemas/validation/index.md)
does before it called anything. A dataclass that `$target` names is checked against
its fields, so `epochs: "50"` arrived as the integer 50, and `batch_size` took its
default ([Dataclass targets](../../schemas/typed-dict-schemas/index.md#dataclass-targets)).
The second argument, `Experiment`, is the class of the result: `instantiate`
checks the result with `isinstance`, and your editor and type checker see an
`Experiment`.

`loss` is a `$symbol` node, and only a node with `$target` is instantiated.

## `$args`

The node's keys are the keyword arguments of the call, and `$args` is a list of
positional ones. `torch.nn.Sequential` takes its layers only by position. For a
dataclass, name the fields instead: `$args` binds its items to the fields by
position, which a reader of the config cannot see.

## `$partial` and `prepare`

The optimizer needs the model's parameters, which exist only once the model is
built. `$partial: true` gave a `functools.partial` of `torch.optim.SGD` with the
config's arguments, which the code called with the parameters. Keyword arguments
of the call win over the config's, as `lr=0.01` did.

`prepare` does the same for the node it gets: `prepare(config, Experiment)` built
the model, optimizer and loss, and left the call of `Experiment` to the code, which
gave `epochs=5`.

## Rules

**Building.**

- A mapping with `$target` is built: the class or function that `$target` names is
  called with the node's other keys as keyword arguments and the items of `$args`
  as positional ones. A class with a `from_config` is built through it instead
  ([Configurable classes](../configurable-classes/index.md)).
- A mapping with `$symbol` is replaced by the object it names, uncalled. Importing
  the module runs the module's top-level code.
- `$target` and `$symbol` take an import path `package.module.Name`; the module is
  imported, any module. A `$target` that is neither callable nor has `from_config`
  raises ``ConfigTargetError: `math.pi` is neither callable nor has `from_config`.
  Use `$symbol` for an object that is used as it is.`` A `$symbol` node holds no
  other key but `$meta`.
- Nested `$target` nodes, in mappings and lists, are built before the node that
  takes them. Two interpolations to one `$target` node build two objects, while a
  `$symbol` read twice gives the same object.
- A `dict` that a resolver returns is passed on as a `dict`, also when it holds
  `$target`.
- `validate`, `instantiate` and `prepare` leave the config they get unchanged.

**`instantiate(config, schema=None)`** takes a node with `$target`, or a `dict`. It
checks the config as `validate` does, so that nothing is called for an invalid
config, then builds it. A root without `$target`, also a `$symbol` node, raises
``ConfigTargetError: There is nothing to instantiate: the root has no
`$target`.``, which names the node instead of "the root" for a node taken from a
config, as `loss` above. `schema` is the class of the result. The result is checked with
`isinstance` against it, also for a function and for a `from_config`, and a
mismatch raises ``ConfigSchemaError: Expected `str`, but `builtins.len` returned
`1`.`` The result is typed as `schema`, or as `Any` without it.

**`$args`.**

- `$args` is a list; anything else raises `ConfigTargetError`.
- A dataclass binds the items to its fields by position and checks each like the
  value of that key. More items than positions, or a key given by `$args` and by
  name, raise `ConfigSchemaError`.
- A class with `from_config` takes its arguments by name and rejects `$args` with
  `ConfigTargetError`.
- A `$base` or an override replaces the list as a whole.

**Partials.**

- `$partial: true` gives a `functools.partial` of the target with the node's
  arguments and `$args`. Its arguments are built once, and every call of the
  partial reuses them. `$partial: false` builds normally. Any other value, also
  `"true"` and `1`, raises `ConfigTargetError`.
- A required key of a dataclass or of a [schema](../configurable-classes/index.md)
  may stay open in a `$partial` node and in the root of `prepare`, to be given at
  the call.
- `prepare(config, schema=None)` is `instantiate` with the call of the root left
  to the caller: it gives a `functools.partial`, typed as a partial of `schema`.
  Nested `$target` nodes are built. A `schema` with a function as the root's
  `$target` raises `ConfigSchemaError`, since what the function returns cannot be
  checked before it is called.

**`make_node(target, /, *args, **kwargs)`** gives the node that calls `target`,
`{"$target": "<module>.<qualname>", **kwargs}`, with `args` under `$args`. Code
that picks a class itself, such as a test or a `from_config`, gets the same checks
as a config does. A class defined inside another class or function, or a
`functools.partial`, raises `ConfigTargetError`, since it cannot be imported by its
path.

**Errors.** The errors of building are `ConfigValidationError`s
([Handling errors](../../guide/errors/index.md)), raised before anything is called:

- `ConfigTargetError` for a node without `$target`, a `$target` that is no import
  path or cannot be called, and a wrong `$args` or `$partial`;
- `ConfigSymbolError` for a `$symbol` that is no import path or stands next to
  other keys;
- `QualifiedNameSyntaxError` for a path that is not of the form
  `package.module.Name`, and `QualifiedNameNotFoundError`, also an `ImportError`,
  for a module or attribute that does not exist;
- `ConfigSchemaError` for a value that does not match its schema
  ([TypedDict schemas](../../schemas/typed-dict-schemas/index.md#rules));
- `ConfigValidationError` for a config that contains itself, as in ``The config
  contains itself: `a` -> `b` -> `a`.``, and for a key that starts with `$` where it
  is not allowed. Every key that starts with `$` is reserved; a `$target` node
  allows `$args`, `$partial` and `$meta`, other mappings only `$meta`.

An error that a module raises while it is imported, and an error of the target or
its `from_config`, keep their type. omegakit adds a note that names the node, as in
``at `model` `` and ``while calling `torch.nn.Linear` at `model` ``.
