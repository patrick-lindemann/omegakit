# Interpolation

omegakit keeps OmegaConf's `${…}` interpolations. A value can refer to another
value of the same config:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
runs/seed0 0 256
runs/seed7 7
```

`${seed}` is resolved when the value is read, not while loading, so the changed
seed reached the run directory and the training split. An override of `seed` does
the same. `${..train.n}` is relative: `..` is the parent of `test`, so the test split
takes the size of the training split wherever the `data` node ends up, for
example after an [import](../imports/index.md).

## Rules

- [Loading](../loading/index.md#rules) says which few values resolve while loading.
  Every other `${…}` resolves when it is read, validated or built, against the
  assembled config. A relative interpolation resolves at the node's final
  position.
- An interpolation that cannot be resolved, or a resolver that raises, raises
  OmegaConf's error when read, such as `InterpolationKeyError`. Validating or
  building raises `ConfigValidationError` instead, with the full key in the
  message, and loading raises `ConfigLoadError` for the values it resolves. Both
  have OmegaConf's error as their `__cause__`.
