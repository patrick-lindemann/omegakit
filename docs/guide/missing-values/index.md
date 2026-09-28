# Missing values

`???` marks a value that someone else must fill, such as the name of an
experiment in a file that every experiment extends:

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

missing keys: {'name'}
error: Missing mandatory value: name
missing keys: set()
config.name: wide
```

Once the name is set, here in code, the config is complete. A file that uses this
one as its `$base`, or an override, fills it the same way. To validate a file that
is incomplete on purpose, see
[Validation](../../schemas/validation/index.md#files-that-are-incomplete-on-purpose).

## Rules

- `???` survives loading. A node that uses its file as `$base`, or an override,
  can fill it.
- Reading a value that is still `???` raises OmegaConf's `MissingMandatoryValue`.
  Validating or building a node that contains one raises `ConfigValidationError`,
  caused by it. Both name the full key.
- `allow_missing=True` in `validate`, and `--allow-missing` in `omegakit check`,
  accept `???`, required fields that are not given, and interpolations to missing
  or unknown keys.
