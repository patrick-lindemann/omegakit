# Interpolation

omegakit keeps OmegaConf's `${…}` interpolations. They resolve against the
assembled config, when a value is read, validated or built.

`curvefit`'s base derives the run directory from the name and the seed, the tracker
writes to that directory, and the training split takes the seed of the run:

```{literalinclude} ../../curvefit/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:lines: 2-9
```

```{literalinclude} ../../curvefit/configs/base.yaml
:language: yaml
:start-at: "tracker:"
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
runs/poly3-adam/seed0 0
runs/poly3-adam/seed7 7
```

`${seed}` was not resolved while loading, so the override of `seed` reached the run
directory, and through it the tracker, and the training split. `${name}` found the
name that the experiment file sets over the `???` of the base. A relative
interpolation such as `${..seed}` resolves from the node's final position, which
lets an imported file refer to its neighbours wherever it is placed.

## Rules

- [Loading](../loading/index.md#rules) says which few values resolve while loading.
  Every other `${…}` resolves when it is read, validated or built, against the
  assembled config. A relative interpolation resolves at the node's final
  position.
- An interpolation that cannot be resolved, or a resolver that raises, raises
  OmegaConf's error when read, such as `InterpolationKeyError`. Validating or
  building raises `ConfigValidationError` instead, with OmegaConf's error as its
  `__cause__` and the full key in the message.
