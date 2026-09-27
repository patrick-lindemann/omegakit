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
ConfigValidationError: Invalid config in `trainer.epochs` (TrainerConfig): Value 'many' of type 'str' could not be converted to Integer
```

- A missing experiment file raises `FileNotFoundError`, as `open` does.
- `OmegaConfBaseException` catches every error that omegakit raises about a config,
  and every error of OmegaConf. Import it from `omegaconf.errors`; the top-level
  `omegaconf` package does not export it.
- `OmegaKitBaseException` catches only omegakit's errors, and
  `ConfigValidationError` only a config that does not match its schema.

`instantiate` validates the config too. Call `validate` on its own to check a config
without building anything, as `omegakit check` does.

## Errors when you read the config

`load_config` leaves interpolations and `???` unresolved, so reading a value can
fail later. OmegaConf raises its own error then, and the same handler catches it:

```{literalinclude} main.py
:language: python
:start-at: config = load_config(f"{configs}/base.yaml")
:end-at: print(f"{type(error).__name__}: {error}")
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
:start-at: run("experiments/poly3-adam.yaml", ["tracker.token=abc"])
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
      └── omegakit.ConfigValidationError   (also omegaconf.errors.ValidationError)
  ```

- `ConfigValidationError` is a `ValueError`. `OmegaKitBaseException` is not.
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
