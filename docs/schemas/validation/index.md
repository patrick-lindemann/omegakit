# Validation

`validate` checks a loaded config against its schemas, and raises
`ConfigValidationError` at the first problem, naming the key:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: incomplete.yaml
```

```{code-block} text
:caption: Output

error: Invalid config in `training.epochs` (Experiment): Value 'many' of type 'str' could not be converted to Integer
error: `training.schedule` must be one of 'constant', 'cosine', but the config gives `'linear'`.
error: `model` expects Module, but the config gives `$class: torch.optim.SGD`.
```

The file itself is valid. Each override broke one check: a value that does not
convert, a value outside its `Literal`, and a `$class` of the wrong class for the
`model: nn.Module` field, caught before anything was built. How fields are checked
is on [Dataclass schemas](../dataclass-schemas/index.md).

## Files that are incomplete on purpose

A file that others complete, such as a base, can leave values open with `???`
([Missing values](../../guide/missing-values/index.md)). `allow_missing=True`
accepts what is missing and still checks every value the file gives:

```{literalinclude} incomplete.yaml
:language: yaml
:caption: incomplete.yaml
```

```{literalinclude} main.py
:language: python
:start-at: incomplete.yaml
```

To check files from a terminal, a pre-commit hook or CI, use
[`omegakit check`](../../command-line/index.md).

## Rules

`validate(config, *, schema=None, allow_missing=False, allowed_modules=None)`
checks an assembled config, or any node of it, and raises `ConfigValidationError`
at the first problem. `load_config` checks no schema. `instantiate` and `prepare`
run this check, with their own `schema`, before building.

- The config is resolved first. A failing interpolation or a `???` is invalid
  unless `allow_missing`. The error names the full key.
- Every `$class` node is checked against its class's schema. Nested `$class`
  nodes are checked before their parent. The class is imported, not called. A
  class without a schema has only its children checked. A class whose schema is
  not supported, or does not fit its `__init__`, raises `SchemaDefinitionError`
  ([Dataclass schemas](../dataclass-schemas/index.md#rules)).
- `schema` says what the root must match. A root with `$class` must name
  `schema` or a subclass. A root without `$class` is checked against the schema
  of `schema`: a dataclass is its own, and a `Configurable` has its `TConfig`. A
  class without one raises. Anything that is not a class raises `TypeError`.
  Without `schema`, only the `$class` nodes are checked.
- `allow_missing=True` accepts `???`, required fields that are not given, and
  interpolations to missing or unknown keys. Given values are still checked.
- An object field accepts a `$class` node of the annotated class or a subclass, a
  `$ref` to an instance, or `null` if optional. It accepts a plain mapping only if
  the annotation is a dataclass (a section). The class check is skipped for
  functions, for `$partial: true`, and for annotations that are not plain classes
  or unions of them, such as `Callable` and `Protocol`. Reserved keys and nested
  nodes are still checked. Any other value raises `ConfigValidationError` naming
  the field, the expected class and what the config gives.
- Reserved keys are checked ([Instantiation](../../objects/instantiation/index.md#rules)).
  What `from_config` returns is not checked.
- `$class` or `$ref` raises `ConfigValidationError`, naming the node, when it is
  not a string or not a dotted path, or names a missing module (or parent package)
  or attribute. The `ImportError` is its `__cause__`. So does
  a `$class` target that is neither callable nor has `from_config`; `$ref` accepts
  any object. An `ImportError` raised by the named module itself, such as for a
  missing dependency, propagates.
- Plain values are checked as `instantiate` converts them: `"64"` is a valid
  `int`. The config is not changed.
- `allowed_modules` limits which modules `$class` and `$ref` may name
  ([Restricting imports](../../security/restricting-imports/index.md#rules)).

**What runs.** No `$class` target, `from_config` or schema dataclass is called;
their `__post_init__` runs once, when building. But the modules named by `$class`
and `$ref` are imported, resolvers run, the `__instancecheck__` and
`__subclasscheck__` of imported classes run, and every `default_factory` runs,
possibly several times and also for fields the config sets. A factory's exception
propagates.
