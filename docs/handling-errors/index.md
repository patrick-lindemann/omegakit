# Handling errors

omegakit's errors derive from OmegaConf's, so one handler around loading, validating
and building a config catches omegakit's errors and OmegaConf's. What your own
classes raise passes through unchanged.

## One handler for the config

`run` loads an experiment, checks it, builds it and reads a value from it:

```{literalinclude} main.py
:language: python
:caption: main.py
:start-at: def run(
:end-at: run("experiments/poly3-adam.yaml", ["trainer.epochs=many"])
```

```text
poly3-adam: runs/poly3-adam/seed3
No such file: poly3-adma.yaml
ConfigLoadError: Cannot parse the override `trainer.epochs=[50`: while parsing a flow sequence: expected ',' or ']', but got '<stream end>' (line 1, column 4)
ConfigValidationError: Invalid config in `trainer.epochs` (TrainerConfig): Value 'many' of type 'str' could not be converted to Integer
```

- A missing experiment file raises `FileNotFoundError`, as `open` does.
- `OmegaConfBaseException` catches every error that omegakit raises about a config,
  and every error of OmegaConf. Import it from `omegaconf.errors`; the top-level
  `omegaconf` package does not export it.
- `OmegaKitBaseException` catches only omegakit's errors. Below it,
  `ConfigLoadError` means a file, an import, a `$base`, a `$defaults` or an
  override is invalid: fix the file or the override. `ConfigValidationError` means
  the values do not match the schema: fix the values. `SchemaDefinitionError` means
  a class cannot serve as a schema: fix the class.

`instantiate` validates the config too. Call `validate` on its own to check a config
without building anything, as `omegakit check` does.

## Errors in a sweep

A sweep runs one experiment per combination of values
([Parameter sweeps](../recipes/parameter-sweeps/index.md)). A combination with an
invalid value can be skipped, but a class that cannot serve as a schema breaks every
run, so the sweep stops:

```{literalinclude} main.py
:language: python
:start-at: for degree in
```

```text
Built degree=3
Skipped degree=three: Invalid config in `model.degree` (Polynomial): Value 'three' of type 'str' could not be converted to Integer
Built degree=5
```

`SchemaDefinitionError` is not a `ConfigValidationError`, so
`except ConfigValidationError` never skips a broken class. A config can still
reach one, when its `$class` names that class.

## Errors when you read the config

`load_config` leaves interpolations and `???` unresolved, so reading a value can
fail later. OmegaConf raises its own error then, and the same handler catches it:

```{literalinclude} main.py
:language: python
:start-at: config = load_config(f"{configs}/base.yaml")
:end-at: print(type(error).__name__, error, sep=": ")
```

```text
MissingMandatoryValue: Missing mandatory value: name
    full_key: name
    object_type=dict
```

A config that passed `validate` resolves without errors, unless a resolver gives a
different result the next time.

## Errors from your constructors

An exception from a class that a config builds propagates as it is, with a note that
names the node. The tracker has no schema, so a key it does not take reaches its
`__init__`, which raises `TypeError`:

```{literalinclude} main.py
:language: python
:start-after: print(type(error).__name__, error, sep=": ")
:end-at: print(error.__notes__)
:lines: 2-
```

```text
Tracker.__init__() got an unexpected keyword argument 'token'
['while instantiating tracker (curvefit.tracking.Tracker)']
```

Give the class a schema to have a key like this rejected with
`ConfigValidationError` before anything is built
([Configurable classes](../objects/configurable-classes/index.md)).

## Rules

- omegakit's errors form this hierarchy:

  ```text
  omegaconf.errors.OmegaConfBaseException
  └── omegakit.OmegaKitBaseException
      ├── omegakit.ConfigLoadError
      ├── omegakit.ConfigValidationError   (also omegaconf.errors.ValidationError)
      └── omegakit.SchemaDefinitionError
  ```

- `load_config` raises `ConfigLoadError`, and so does an invalid override in any
  function. `validate`, `instantiate` and `prepare` raise `ConfigValidationError`
  for what they check.
- A class that cannot serve as a schema raises `SchemaDefinitionError` wherever it
  is reached: in `check_schema`, `generate_json_schema`, or a `$class` that
  `validate`, `instantiate` or `prepare` checks.
- `ConfigLoadError`, `ConfigValidationError` and `SchemaDefinitionError` are
  `ValueError`s. `OmegaKitBaseException` is not.
- An error of omegakit carries its message, with OmegaConf's error or another cause
  as `__cause__` where there is one.
- A missing root file raises `FileNotFoundError`. An `import_root` that is not a
  directory raises `NotADirectoryError`.
- API misuse raises `TypeError`: a `schema` that is not a class, `allowed_modules`
  given as a string, or overrides of an unsupported type.
- Reading a loaded config raises OmegaConf's errors, such as `MissingMandatoryValue`
  or `InterpolationResolutionError`.
- An exception from a constructor or a `from_config` propagates unwrapped, with a
  note naming the node.
- An exception from a resolver arrives as OmegaConf's
  `InterpolationResolutionError` when a value is read, and as an error of omegakit,
  caused by it, from the functions that resolve the config.
