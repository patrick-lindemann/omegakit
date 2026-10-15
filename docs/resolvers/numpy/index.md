# NumPy

`omegakit.resolvers.numpy` lets a config name NumPy data types. NumPy is not a
dependency of omegakit: install it first ([Overview](../overview/index.md#rules)).

```{literalinclude} arrays.yaml
:language: yaml
:caption: arrays.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

config.dtype: dtype('float32')
config.labels_dtype: dtype('int64')
inputs.dtype: float32
```

`${numpy.dtype:float32}` resolves to the `numpy.dtype` object, which NumPy accepts
wherever it takes a `dtype`.

## Rules

- `${numpy.dtype:<name>}` gives `numpy.dtype(<name>)`, such as `float32` or
  `int64`. A name that NumPy does not know raises
  ``TypeError: data type 'float33' not understood`` in the resolver: reading the
  value raises OmegaConf's `InterpolationResolutionError`, and `validate`,
  `instantiate` and `prepare` raise `ValidationInterpolationError`
  ([Interpolation](../../guide/interpolation/index.md#rules)).
- `register_numpy_resolvers(*, replace=False, use_cache=True)` registers every NumPy
  resolver, which is `numpy.dtype`. `register_numpy_dtype_resolver` registers it
  alone, with the same arguments ([Overview](../overview/index.md#rules)).
- Importing `omegakit.resolvers.numpy` imports NumPy, and raises `ImportError`
  without it.
