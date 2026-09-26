# Interpolation and `???`

omegakit keeps OmegaConf's `${…}` interpolations and `???` missing values, and
resolves them against the fully assembled config.

## Example

A library file leaves `host` open with `???` and builds `url` from interpolations:

```{literalinclude} ../examples/interpolation-and-missing/library.yaml
:language: yaml
:caption: library.yaml
```

```{literalinclude} ../examples/interpolation-and-missing/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/interpolation-and-missing/main.py
:language: python
:caption: main.py
```

## When interpolations resolve

- Only structural values resolve during loading: the path of an `~import`, and the
  values of `$base` and `$defaults`.
- Every other `${…}` resolves when it is read or instantiated, against the assembled
  config. `${database}` in the library file finds the key in `app.yaml`.
- A relative interpolation such as `${.host}` resolves at the node's final position,
  so each consumer of the library gets its own `url`.

## `???`

- A `???` survives loading. A consumer of the `$base` that carries it, or an
  override, can fill it.
- Reading a value that is still missing raises `MissingMandatoryValue`, naming the
  full key. Reading an interpolation that points at it raises
  `InterpolationToMissingValueError`.
- `instantiate` raises for any `???` in the node it builds, and `validate` reports it
  without building anything.
