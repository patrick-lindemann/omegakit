# Torch

`omegakit.resolvers.torch` lets a config name PyTorch data types and check for a
GPU. PyTorch is not a dependency of omegakit: install it for your platform first
([Overview](../overview/index.md#resolvers-for-other-libraries)). Register the
resolvers before loading the configs that use them:

```{literalinclude} precision.yaml
:language: yaml
:caption: precision.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
torch.bfloat16 torch.bfloat16 False
```

`${dtype:bfloat16}` resolves to `torch.bfloat16`, the object itself, which PyTorch
accepts wherever it takes a `dtype`. An override such as `'dtype=${dtype:float32}'`
picks another type. `${cuda_available:}` resolves to `True` when PyTorch can use
CUDA on this machine, for a config that chooses its device.

## Rules

- `${dtype:<name>}` gives the `torch.dtype` named `<name>`, such as `float32` or
  `bfloat16`. A name that is not a dtype fails like any resolver error: reading it
  raises OmegaConf's `InterpolationResolutionError`, and validating or building
  raises `ConfigValidationError` ([Interpolation](../../guide/interpolation/index.md#rules)).
- `${cuda_available:}` gives `torch.cuda.is_available()`.
- `register_torch_resolvers()` registers both. `register_torch_dtype_resolver()`
  and `register_cuda_available_resolver()` register one each.
- `register_torch_resolvers()` registers neither if either name is already
  registered, and raises `ValueError`, unless `replace=True`.
- Registering without PyTorch installed raises `ImportError`. Importing the module
  does not import PyTorch.
