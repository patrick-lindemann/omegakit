# Overview

A resolver is a function inside an interpolation, such as `${oc.env:TRACKER_TOKEN}`.
OmegaConf's own resolvers, such as `oc.env`, are always available;
[Environment variables](../../configs/environment-variables/index.md) shows `oc.env`
in use.

omegakit adds optional resolvers. Each module under `omegakit.resolvers` holds the
resolvers for one purpose, and has a page in this section, except
`omegakit.resolvers.secrets`, which is on [Secrets](../../security/secrets/index.md).
Register the ones you need once, before loading the configs that use them:

```python
from omegakit.resolvers.paths import register_paths_resolver

register_paths_resolver({"runs": "/scratch/runs"})
```

## Resolvers for other libraries

Some resolvers need a library that omegakit does not depend on, such as
[Torch](../torch/index.md). Such a library is required only when you register its
resolvers, not when you install omegakit. Install it yourself, in the version and
build your platform needs.

## Rules

- OmegaConf's own resolvers, such as `oc.env`, are always available. omegakit does
  not change them.
- omegakit's resolvers are opt-in. Each is imported from its own module, and
  `omegakit.resolvers` itself exports nothing. Importing omegakit, or a resolver
  module, registers no resolver and imports no optional library.
- Registering the resolvers of a library that is not installed raises
  `ImportError`, naming what to install.
- Registration is global to OmegaConf. Registering a name that exists raises
  `ValueError` unless `replace=True`.
- omegakit's resolvers cache their results per config. A config that has resolved
  `${paths:runs}` keeps that value after the resolver is replaced. A config loaded
  afterwards sees the new one.
- The [API](../../api/index.md#resolvers) lists every resolver module and function.
