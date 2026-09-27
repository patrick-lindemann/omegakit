# Overview

A resolver is a function inside an interpolation, such as `${oc.env:SECRET_KEY}`.
OmegaConf's own resolvers, such as `oc.env`, are always available;
[Overrides and environment variables](../../configs/overrides/index.md) shows `oc.env`
in use.

omegakit adds optional resolvers. Each module under `omegakit.resolvers` holds the
resolvers for one purpose, and has a page in this section. Register the ones you
need once, before loading the configs that use them:

```python
from omegakit.resolvers.paths import register_paths_resolver

register_paths_resolver({"logs": "/var/log"})
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
- The [API](../../api/index.md#resolvers) lists every resolver module and function.
