# Overview

A resolver is a function inside an interpolation, such as `${oc.env:TRACKER_TOKEN}`.
[Environment variables](../../guide/environment-variables/index.md) shows OmegaConf's
`oc.env` in use.

omegakit adds optional resolvers. Each module under `omegakit.resolvers` holds the
resolvers for one purpose, and has a page in this section, except
`omegakit.resolvers.secrets`, which is on [Secrets](../../security/secrets/index.md).
Register the ones you need once, before loading the configs that use them:

```python
from omegakit.resolvers.paths import register_paths_resolver

register_paths_resolver({"runs": "/scratch/runs"})
```

## Your own resolvers

Register a resolver of your own with `register_resolver` from `omegakit.resolvers`.
It registers the resolver as omegakit registers its own:

```{literalinclude} train.yaml
:language: yaml
:caption: train.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

config.steps_per_epoch: 16
```

`${batches:...}` received the resolved values of `data.train` and `batch_size`, and
its result replaced the interpolation.

## Resolvers for other libraries

Some resolvers need a library that omegakit does not depend on, such as
[Torch](../torch/index.md). Install it yourself, in the version and build your
platform needs.

## Rules

- OmegaConf's own resolvers, such as `oc.env`, are always available. omegakit does
  not change them.
- omegakit's resolvers are opt-in. Each is imported from its own module, and
  `omegakit.resolvers` itself exports only `register_resolver`. Importing omegakit,
  or a resolver module, registers no resolver and imports no optional library.
- `register_resolver(name, resolver, *, replace=False)` registers `resolver` under
  `name` through `OmegaConf.register_resolver`, cached. Its arguments are not
  checked against the resolver's annotations.
- Registering the resolvers of a library that is not installed raises
  `ImportError`, naming what to install.
- Registration is global to OmegaConf. Registering a name that exists raises
  `ValueError` unless `replace=True`.
- Resolvers registered with `register_resolver`, omegakit's included, cache their
  results per config. A config that has resolved
  `${paths:runs}` keeps that value after the resolver is replaced. A config loaded
  afterwards sees the new one.
- The [API](../../reference/api/index.md#resolvers) lists every resolver module and function.
