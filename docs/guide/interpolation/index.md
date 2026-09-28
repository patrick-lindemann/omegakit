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

```{code-block} text
:caption: Output

config.run_dir: runs/seed0
config.data.train.seed: 0
config.data.test.n: 256
config.run_dir: runs/seed7
config.data.train.seed: 7
```

`${seed}` was resolved when the value was read, so the changed seed reached the run
directory and the training split. An override of `seed` does the same. In
`${..train.n}`, `..` is the parent of `test`, so the test split takes the size of the
training split wherever the `data` node ends up, for example after an
[import](../imports/index.md).

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
