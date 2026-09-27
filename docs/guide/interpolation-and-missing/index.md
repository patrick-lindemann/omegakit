# Interpolation and missing values

omegakit keeps OmegaConf's `${…}` interpolations and `???` missing values. Both
resolve against the assembled config, when a value is read, validated or built.

`webapp`'s shared settings build the cache URL from the server's host, and leave the
secret key open for each environment to fill:

```{literalinclude} ../../webapp/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:end-before: "database:"
```

```{literalinclude} ../../webapp/configs/base.yaml
:language: yaml
:start-at: "cache:"
:end-before: "jobs:"
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
redis://127.0.0.1:6379
redis://10.0.0.5:6379
Cannot resolve `server.secret_key`: Missing mandatory value: secret_key
```

`${server.host}` was not resolved while loading, so the override of `server.host`
reached the cache URL. A relative interpolation such as `${.host}` resolves from the
node's final position, which lets an imported file refer to its neighbours wherever
it is placed.

## Missing values

`???` marks a value that someone else must fill. It survives loading, and a file
that uses this one as its `$base`, or an override, can fill it: `dev.yaml` sets
`secret_key`, and production reads it from the environment. A `???` that is still
open when the config is validated or built raises `ConfigValidationError`, naming
the key.

A file such as `base.yaml` is incomplete on purpose. `validate(base,
allow_missing=True)` still checks every value it does give, and
`omegakit check base.yaml --allow-missing` does the same from the command line
([Validation](../validation/index.md)).

## Rules

- [Loading](../loading/index.md#rules) says which few values resolve while loading. Every
  other `${…}` resolves when it is read, validated or built, against the
  assembled config. A relative interpolation resolves at the node's final
  position.
- `???` survives loading. A node that uses its file as `$base`, or an override,
  can fill it.
- Reading a value that is still `???` raises OmegaConf's `MissingMandatoryValue`.
  Validating or building a node that contains one raises `ConfigValidationError`,
  caused by it. Both name the full key. `allow_missing=True` accepts it in
  `validate` and `omegakit check`.
- An interpolation that cannot be resolved, or a resolver that raises, behaves the
  same: OmegaConf's error when read, `ConfigValidationError` caused by it when
  validated or built.
