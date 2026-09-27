# Resolvers

A resolver is a function inside an interpolation, such as `${oc.env:SECRET_KEY}`.
OmegaConf provides `oc.env` and a few others, which are always available;
[Overrides and environment variables](overrides.md) shows `oc.env` in use. omegakit
adds optional resolvers. Each lives in its own module under `omegakit.resolvers`,
and you register the ones you need before loading a config.

## Paths

`register_paths_resolver` registers `${paths:<key>}`, so a config can name
directories that the application decides:

```{literalinclude} ../examples/guide/resolvers/main.py
:language: python
:caption: main.py
```

```text
/var/log/webapp
```

The paths are copied as strings when the resolver is registered. Relative paths stay
relative, and an unknown key gives `None`.

## Resolvers for other libraries

Some resolvers need a library that omegakit does not depend on. Such a library is
required only when you register its resolvers, not when you install omegakit.
Importing the resolver module does not import the library, and registering without
it raises `ImportError` that names what to install.

The Torch resolvers are one example. `omegakit.resolvers.torch` registers
`${dtype:<name>}`, which gives a `torch.dtype` such as `torch.float16`, and
`${cuda_available:}`:

```python
from omegakit.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
# dtype: ${dtype:float16}
# use_cuda: ${cuda_available:}
```

`register_torch_dtype_resolver()` and `register_cuda_available_resolver()` register
one each. The [API](../api.md#resolvers) lists every resolver module.

## Rules

- OmegaConf's own resolvers, such as `oc.env`, are always available. omegakit does
  not change them.
- omegakit's resolvers are opt-in. Each is imported from its own module, and
  `omegakit.resolvers` itself exports nothing. Importing omegakit, or a resolver
  module, registers no resolver and imports no optional library.
- A resolver module for a library raises `ImportError` when you register its
  resolvers and the library is not installed.
- Registration is global to OmegaConf. Registering a name that exists raises
  `ValueError` unless `replace=True`. Register resolvers once, before loading the
  configs that use them.
