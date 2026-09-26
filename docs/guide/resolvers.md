# Resolvers

Resolvers are OmegaConf's functions inside interpolations, such as `${paths:data}`.
omegakit ships optional ones in separate modules. Nothing is registered on import.

## Example

```{literalinclude} ../examples/resolvers/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/resolvers/main.py
:language: python
:caption: main.py
```

## Paths

`register_paths_resolver(paths)` from `omegakit.resolvers.paths` registers
`${paths:<key>}`. It copies the given paths as strings when it is called. Relative
paths stay relative, and an unknown key gives `None`.

## Torch

`omegakit.resolvers.torch` registers `${dtype:<name>}`, which gives a `torch.dtype`
such as `torch.float16`, and `${cuda_available:}`. PyTorch is not a dependency of
omegakit; install it for your platform first. Importing the module does not import
Torch, and registering without it raises `ImportError`.

`register_torch_resolvers()` registers both. `register_torch_dtype_resolver()` and
`register_cuda_available_resolver()` register one each.

## Rules

- Register resolvers before loading configs that use them.
- Registration is global to OmegaConf. Registering an existing name raises
  `ValueError` unless `replace=True` is passed.
- Results are cached per config. Replacing a resolver does not clear the caches of
  configs that already used it.
- `omegakit.resolvers` itself exports nothing, so each module's dependencies stay
  visible where it is imported.
