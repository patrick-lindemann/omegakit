# Paths

`omegakit.resolvers.paths` lets a config name directories that the machine decides.
The same experiment runs on a laptop and on a cluster, with its runs and its data
in different places. `register_paths_resolver` registers `${paths:<key>}`:

```{literalinclude} cluster.yaml
:language: yaml
:caption: cluster.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
runs/mlp/seed0 data/sine
/scratch/runs/mlp/seed0 /datasets/sine
```

`${paths:runs}` and `${paths:data}` work inside longer strings, like any
interpolation. Register the paths once, when the program starts, from whatever tells
your machines apart, such as the hostname or an environment variable.

## Rules

- `register_paths_resolver(paths, *, replace=False)` takes a mapping from keys to
  paths, as strings or `Path` objects.
- The paths are copied and converted to strings when the resolver is registered.
  Changing the mapping later has no effect. Relative paths stay relative.
- `${paths:<key>}` gives the path registered under `<key>`, and `None` for an
  unknown key.
- Registering again raises `ValueError` unless `replace=True`, which replaces the
  whole mapping ([Overview](../overview/index.md#rules)).
