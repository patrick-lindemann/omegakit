# Handling errors

omegakit's errors derive from OmegaConf's, so one handler around loading and
building a config catches omegakit's errors and OmegaConf's. What your own classes
raise passes through unchanged.

## One handler for the config

`run` loads an experiment and builds it. The script runs it on a valid file, a
missing file, a file whose `$base` lacks its `~import`, and a value of the wrong
type:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} broken.yaml
:language: yaml
:caption: broken.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-at: run("experiment.yaml", ["epochs=many"])
```

```{code-block} text
:caption: Output

experiment.epochs: 50
missing file: experment.yaml
ConfigLoadError: `$base` in `<root>` is not a dictionary or a list of dictionaries.
ConfigValidationError: Invalid config in `epochs` (Experiment): Value 'many' of type 'str' could not be converted to Integer
```

- `OmegaConfBaseException` catches every error that omegakit raises about a config,
  and every error of OmegaConf. Import it from `omegaconf.errors`; the top-level
  `omegaconf` package does not export it.
- `OmegaKitBaseException` catches only omegakit's errors. Below it,
  `ConfigLoadError` means a file, an import, a `$base`, a `$defaults` or an
  override is invalid: fix the file or the override. `ConfigValidationError` means
  the values do not match the schema: fix the values. `SchemaDefinitionError` means
  a class cannot serve as a schema: fix the class.
- A missing experiment file is not a config error. It raises `FileNotFoundError`,
  which `run` catches separately.

## Errors when you read the config

`load_config` leaves interpolations and `???` unresolved, so reading a value can
fail later. OmegaConf raises its own error then, and the same handler catches it:

```{literalinclude} untitled.yaml
:language: yaml
:caption: untitled.yaml
```

```{literalinclude} main.py
:language: python
:start-at: config = load_config("untitled.yaml")
:end-at: print(f"{type(error).__name__}:", error)
```

```{code-block} text
:caption: Output

MissingMandatoryValue: Missing mandatory value: name
    full_key: name
    object_type=dict
```



## Errors from constructors

`torch.nn.Linear` has no schema, so a key it does not take reaches its `__init__`.
The `TypeError` propagates as it is, with a note that names the node:

```{literalinclude} main.py
:language: python
:start-at: run("experiment.yaml", ["model.hidden=64"])
:prepend: "try:"
```

```{code-block} text
:caption: Output

error: Linear.__init__() got an unexpected keyword argument 'hidden'
error.__notes__: ['while instantiating model (torch.nn.Linear)']
```

A class with a schema rejects a key like this with `ConfigValidationError` before
anything is built ([Configurable classes](../../objects/configurable-classes/index.md)).

## Rules

- omegakit's errors form this hierarchy:

  ```text
  omegaconf.errors.OmegaConfBaseException
  └── omegakit.OmegaKitBaseException
      ├── omegakit.ConfigLoadError
      ├── omegakit.ConfigValidationError   (also omegaconf.errors.ValidationError)
      └── omegakit.SchemaDefinitionError
  ```

- `ConfigLoadError`, `ConfigValidationError` and `SchemaDefinitionError` are
  `ValueError`s. `OmegaKitBaseException` is not.
- The class says what is wrong, not which function raised it: an invalid override
  is a `ConfigLoadError` in every function, and a class that cannot serve as a
  schema is a `SchemaDefinitionError` wherever it is reached.
- An error of omegakit carries its message, with OmegaConf's error or another cause
  as `__cause__` where there is one.
- Errors that are not omegakit's keep their type: `FileNotFoundError` for a missing
  file, `TypeError` for API misuse, OmegaConf's errors when a loaded config is read,
  and exceptions from constructors. The Rules of each feature page say which errors
  it raises.
