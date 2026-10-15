# Handling errors

Every error that omegakit raises about a config is an `OmegaKitBaseException`, and
its class says what is wrong. One handler around loading and building a config
catches them, together with OmegaConf's errors. What your own classes raise passes
through unchanged.

## One handler for the config

`run` loads an experiment, checks it and builds its model. The script runs it on a
valid file, a missing file, a file whose `$base` lacks its `~include`, and a value
of the wrong type:

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

epochs: 50 model: Linear(in_features=1, out_features=1, bias=True)
missing file: experment.yaml
ConfigMergeError: `$base` must be a mapping or a list of mappings, not `'experiment.yaml'`. (at the root)
ConfigSchemaError: The value does not match `ExperimentConfig`: Value 'many' of type 'str' could not be converted to Integer (at `epochs`)
```

- `OmegaKitBaseException` catches every error of omegakit, and
  `OmegaConfBaseException` every error of OmegaConf. Import the second from
  `omegaconf.errors`; the top-level `omegaconf` package does not export it.
- Below `OmegaKitBaseException`, `ConfigLoadError` means that a file, an include,
  a `$base`, an `$each` or an override is invalid: fix the file or the override.
  `ConfigValidationError` means that the values do not fit their schema or cannot
  be built: fix the values. `SchemaDefinitionError` means that a class cannot serve
  as a schema: fix the class. `ConfigMergeError` and `ConfigSchemaError` are two of
  their subclasses; the [API](../../reference/api/index.md) lists all.
- A missing file raises `ConfigFileNotFoundError`, a `ConfigLoadError` that is also
  a `FileNotFoundError`. `run` catches it as the builtin error and reads the file
  from `filename`.

## The place of an error

`str(error)` is the message followed by its place, and the error also holds the
place as data:

```{literalinclude} main.py
:language: python
:start-after: run("experiment.yaml", ["epochs=many"])
:end-at: print("error.full_key:", error.full_key)
```

```{code-block} text
:caption: Output

error.message: The value does not match `ExperimentConfig`: Value 'many' of type 'str' could not be converted to Integer
error.full_key: epochs
```

`full_key` is the key of the node at fault, such as `items[0].model`, `""` for the
root, and `None` where the error concerns no node. `file_path` is the config file
at fault, set by an error of an [include](../includes/index.md#rules), and `None`
elsewhere.

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

`validate`, `instantiate` and `prepare` report the same value as
``ValidationMissingValueError: The value is `???`. Set it in the config or with an
override. (at `name`)`` ([Missing values](../missing-values/index.md#rules)).

## Errors from constructors

`torch.nn.Linear` has no schema, so a key it does not take reaches its `__init__`.
The `TypeError` passes through `run` as it is, with a note that names the node:

```{literalinclude} main.py
:language: python
:start-at: run("experiment.yaml", ["model.hidden=64"])
:prepend: "try:"
```

```{code-block} text
:caption: Output

error: Linear.__init__() got an unexpected keyword argument 'hidden'
error.__notes__: ['  while calling `torch.nn.Linear` at `model`']
```

A class with a schema rejects a key like this with a `ConfigSchemaError` before
anything is built ([Configurable classes](../../objects/configurable-classes/index.md)).

## Rules

- omegakit's errors form three families:

  ```text
  Exception
  └── omegakit.OmegaKitBaseException
      ├── omegakit.ConfigLoadError         load_config
      ├── omegakit.ConfigValidationError   validate, instantiate, prepare
      └── omegakit.SchemaDefinitionError   a schema that cannot check a config
  ```

  `OmegaKitBaseException` is no OmegaConf error, `ValueError` or `TypeError`.
  `ConfigFileNotFoundError` is also a `FileNotFoundError`,
  `ConfigFilePermissionError` a `PermissionError`, and
  `QualifiedNameNotFoundError`, for a `$target` or `$symbol` that cannot be
  imported, an `ImportError`.
- The class says what is wrong, not which function raised it: a schema that cannot
  check a config is a `SchemaDefinitionError` wherever it is reached.
- `str(error)` is `error.message` followed by the place: ``(at `model.depth`)``,
  ``(at the root)``, or with the file of an include, ``(at `model` in
  `…/large.yaml`)``. A key keeps the brackets of a list index, as in
  `items[0].model`. Where an error has a cause, such as OmegaConf's error, it is the
  `__cause__`.
- Errors that are not omegakit's keep their type: OmegaConf's errors when a loaded
  config is read, an `OSError` while a file is read, and what a constructor or
  `from_config` raises. omegakit adds a note to the last, as in ``while calling
  `torch.nn.Linear` at `model` ``, and to an error that a module raises while
  `$target` or `$symbol` imports it, as in ``at `model` ``. The Rules of each
  feature page say which errors it raises.
