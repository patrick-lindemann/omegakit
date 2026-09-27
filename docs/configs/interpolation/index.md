# Interpolation

omegakit keeps OmegaConf's `${…}` interpolations. They resolve against the
assembled config, when a value is read, validated or built.

`webapp`'s shared settings build the cache URL from the server's host:

```{literalinclude} ../../webapp/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
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
```

`${server.host}` was not resolved while loading, so the override of `server.host`
reached the cache URL. A relative interpolation such as `${.host}` resolves from the
node's final position, which lets an imported file refer to its neighbours wherever
it is placed.

## Rules

- [Loading](../loading/index.md#rules) says which few values resolve while loading.
  Every other `${…}` resolves when it is read, validated or built, against the
  assembled config. A relative interpolation resolves at the node's final
  position.
- An interpolation that cannot be resolved, or a resolver that raises, raises
  OmegaConf's error when read, such as `InterpolationKeyError`. Validating or
  building raises `ConfigValidationError` instead, with OmegaConf's error as its
  `__cause__` and the full key in the message.
