# Paths

`omegakit.resolvers.paths` lets a config name directories that the application
decides. `register_paths_resolver` registers `${paths:<key>}`:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
/var/log/webapp
```

The override above uses the resolver inside a longer string, so `log_dir` ends up
below the registered directory.

## Rules

- `register_paths_resolver(paths, *, replace=False)` takes a mapping from keys to
  paths, as strings or `Path` objects.
- The paths are copied and converted to strings when the resolver is registered.
  Changing the mapping later has no effect. Relative paths stay relative.
- `${paths:<key>}` gives the path registered under `<key>`, and `None` for an
  unknown key.
- Registering again raises `ValueError` unless `replace=True`, which replaces the
  whole mapping ([Overview](../overview/index.md#rules)).
