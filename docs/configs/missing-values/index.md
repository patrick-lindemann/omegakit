# Missing values

`???` marks a value that someone else must fill. `webapp`'s shared settings leave
the secret key open for each environment:

```{literalinclude} ../../webapp/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:end-before: "database:"
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
Cannot resolve `server.secret_key`: Missing mandatory value: secret_key
```

A file that uses this one as its `$base`, or an override, can fill the value:
`dev.yaml` sets `secret_key`, and production reads it from the environment. A `???`
that is still open when the config is validated or built raises
`ConfigValidationError`, naming the key.

A file such as `base.yaml` is incomplete on purpose. `validate(base,
allow_missing=True)` still checks every value it does give, and
`omegakit check base.yaml --allow-missing` does the same from the command line
([Validation](../../objects/validation/index.md)).

## Rules

- `???` survives loading. A node that uses its file as `$base`, or an override,
  can fill it.
- Reading a value that is still `???` raises OmegaConf's `MissingMandatoryValue`.
  Validating or building a node that contains one raises `ConfigValidationError`,
  caused by it. Both name the full key.
- `allow_missing=True` in `validate`, and `--allow-missing` in `omegakit check`,
  accept `???`, required fields that are not given, and interpolations to missing
  or unknown keys.
