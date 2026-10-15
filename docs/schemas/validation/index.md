# Validation

`validate` checks a loaded config against a schema without building anything, and
raises a `ConfigValidationError` at the first problem, placed at its key:

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

ConfigSchemaError: The value does not match `TrainingConfig`: Value 'many' of type 'str' could not be converted to Integer (at `training.epochs`)
ConfigSchemaError: The value does not match `TrainingConfig`: Invalid value 'linear', expected one of ['constant', 'cosine'] (at `training.schedule`)
ConfigSchemaError: Expected `Module`, but the config gives `$target: torch.optim.SGD`. (at `model`)
```

The file itself is valid. Each override broke one check: a value that does not
convert to an `int`, a value outside its `Literal`, and a `$target` of a class that
is no `nn.Module`. `torch.optim.SGD` was imported to check its class, but not
called. How each key is checked is on
[TypedDict schemas](../typed-dict-schemas/index.md).

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

```{code-block} text
:caption: Output

is_valid: False
allow_missing: True
ConfigSchemaError: The value does not match `TrainingConfig`: Invalid value 'linear', expected one of ['constant', 'cosine'] (at `training.schedule`)
```

`is_valid` takes the arguments of `validate` and returns `False` where `validate`
raises a `ConfigValidationError`. With `allow_missing=True`, the `???` of `epochs`
and the `model` that the file does not give passed, while the wrong `schedule` of
the override did not.

To check files from a terminal, a pre-commit hook or CI, use
[`omegakit check`](../../command-line/check/index.md), which loads each file with
`load_config` and checks it with `validate`. Its `--allow-missing` is the
`allow_missing` of `validate`.

## Rules

`validate(config, schema=None, *, allow_missing=False)` checks a config, a `dict`,
a `list` or a `tuple`, returns `None`, and raises at the first problem.
`is_valid(config, schema=None, *, allow_missing=False)` returns `False` for a
`ConfigValidationError` instead. Neither catches a `SchemaDefinitionError`.
`load_config` checks no schema, and `instantiate` and `prepare` run this check
before they call anything ([Instantiation](../../objects/instantiation/index.md#rules)).

**What it checks.**

- `schema` is the type that the root must give: a `TypedDict` for a root without
  `$target`, a class for a root with `$target`, which must name the class or a
  subclass. A `schema` that is no class raises `SchemaDefinitionError`. Without
  `schema`, the config itself is checked.
- Every `$target` node is checked against the schema of its class, nested nodes
  first: the `schema` of a `Configurable`, or the fields of a dataclass
  ([TypedDict schemas](../typed-dict-schemas/index.md#rules)). A class without
  either has only the nodes inside its arguments checked.
- The class or object that every `$target` and `$symbol` names is imported, and
  none is called. A path that cannot be imported raises
  `QualifiedNameNotFoundError` or `QualifiedNameSyntaxError`.
- Every key that starts with `$` where it is not allowed raises
  `ConfigValidationError` ([Instantiation](../../objects/instantiation/index.md#rules)).
- Interpolations are resolved as the values are read. One that cannot be resolved
  raises `ValidationInterpolationError`, and a `???` raises ``ValidationMissingValueError:
  The value is `???`. Set it in the config or with an override. (at
  `training.epochs`)``.
- The config is not changed.

**`allow_missing=True`** accepts a `???`, also a root that is `???`, a required key
that is not given, and an interpolation to a missing or unknown key. Such a missing
value fits every annotation and is not converted, nor is a list, tuple or mapping
of data that holds one. Every other value is still checked. The special keys still
need their values: a `$target`, `$symbol`, `$args` or `$partial` that is missing
raises. An interpolation that fails for another reason, such as an unset
environment variable, raises as well. `instantiate` and `prepare` have no
`allow_missing`.

**What runs.** The top-level code of the modules that `$target` and `$symbol`
name, the resolvers of the config, and the `__instancecheck__` and
`__subclasscheck__` of the classes in a schema. No target, `from_config`,
`default_factory` or `__post_init__` of your classes is called.
