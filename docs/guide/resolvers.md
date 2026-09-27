# Resolvers

A resolver is a function inside an interpolation, such as `${oc.env:SECRET_KEY}`.
OmegaConf provides `oc.env` and a few others; omegakit adds optional resolvers in
separate modules, and registers nothing on import.

## Environment variables

`${oc.env:NAME}` reads an environment variable, and `${oc.env:NAME,default}` falls
back to a default. It is always available. `webapp` uses it to pick the environment
and to read its production secret; see
[Overrides and environment variables](overrides.md).

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

## Torch, for PyTorch users

`omegakit.resolvers.torch` registers `${dtype:<name>}`, which gives a `torch.dtype`
such as `torch.float16`, and `${cuda_available:}`. PyTorch is not a dependency of
omegakit, so install it for your platform first:

```python
from omegakit.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
# dtype: ${dtype:float16}
# use_cuda: ${cuda_available:}
```

Importing the module does not import Torch, and registering without it raises
`ImportError`. `register_torch_dtype_resolver()` and
`register_cuda_available_resolver()` register one each.

Register resolvers once, before loading the configs that use them. Registration is
global to OmegaConf, and a name that is already registered raises `ValueError`
unless you pass `replace=True`.

## Rules

- OmegaConf's own resolvers, such as `oc.env`, are always available. omegakit does
  not change them.
- omegakit's resolvers are opt-in. Each is imported from its own module, and
  `omegakit.resolvers` itself exports nothing. Importing omegakit registers no
  resolver.
- Registration is global to OmegaConf. Registering a name that exists raises
  `ValueError` unless `replace=True`.
- Resolvers are registered through the API of the installed OmegaConf version, so
  no version warns.
