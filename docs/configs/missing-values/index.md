# Missing values

`???` marks a value that someone else must fill. `curvefit`'s base leaves the name
of the experiment open, because every experiment file sets its own:

```{literalinclude} ../../curvefit/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:lines: 2-4
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
Cannot resolve `name`: Missing mandatory value: name
```

A file that uses this one as its `$base`, or an override, can fill the value. A
`???` that is still open when the config is validated or built raises
`ConfigValidationError`, naming the key.

A file such as `base.yaml` is incomplete on purpose: it also has no model and no
optimizer, which the schema requires. `allow_missing=True` accepts all of that, and
the run directory that refers to the open name, and still checks every value the
file does give. `omegakit check configs/base.yaml --allow-missing` does the same
from the command line ([Validation](../../objects/validation/index.md)).

## Rules

- `???` survives loading. A node that uses its file as `$base`, or an override,
  can fill it.
- Reading a value that is still `???` raises OmegaConf's `MissingMandatoryValue`.
  Validating or building a node that contains one raises `ConfigValidationError`,
  caused by it. Both name the full key.
- `allow_missing=True` in `validate`, and `--allow-missing` in `omegakit check`,
  accept `???`, required fields that are not given, and interpolations to missing
  or unknown keys.
