# Overview

A resolver is a function inside an interpolation, such as `${oc.env:TRACKER_TOKEN}`.
[Environment variables](../../guide/environment-variables/index.md) shows OmegaConf's
`oc.env` in use.

omegakit adds optional resolvers, one module under `omegakit.resolvers` for each
purpose or library, each with a page in this section:
[Paths](../paths/index.md), [Torch](../torch/index.md) and [NumPy](../numpy/index.md).
`omegakit.resolvers.secrets` is on [Secrets](../../security/secrets/index.md).
Register the ones you need once, before the configs that use them are read:

```python
from omegakit.resolvers.paths import register_paths_resolver

register_paths_resolver({"runs": "/scratch/runs"})
```

## Rules

- OmegaConf's own resolvers, such as `oc.env`, are always available. omegakit does
  not change them.
- Importing `omegakit` registers no resolver, and `omegakit.resolvers` exports
  nothing. Each module registers its resolvers through its `register_*` functions.
  The `omegakit` command registers `${secret:...}` itself.
- Every `register_*` function takes `replace=False` and `use_cache=True` and passes
  them to `OmegaConf.register_resolver`. Registration is global to OmegaConf.
- A name that is registered already raises
  ``ValueError: resolver 'paths' is already registered``, unless `replace=True`. A
  function that registers several resolvers registers them one after the other, so
  the ones before the name that is taken stay registered.
- With `use_cache=True`, a config keeps the result of a resolver for the same
  arguments: a config that has read `${paths:runs}` keeps that value after the
  resolver is replaced, and a config loaded afterwards sees the new one. With
  `use_cache=False`, every read calls the resolver.
- `omegakit.resolvers.torch` and `omegakit.resolvers.numpy` import their library
  when they are imported, and raise `ImportError` without it. omegakit depends on
  neither: install the library yourself, in the version and build your platform
  needs.
- The [API](../../reference/api/index.md#resolvers) lists every resolver module and
  function.
