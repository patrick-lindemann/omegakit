# Torch

`omegakit.resolvers.torch` lets a config name PyTorch data types and check for a
GPU. PyTorch is not a dependency of omegakit: install it for your platform first
([Overview](../overview/index.md#resolvers-for-other-libraries)).

```python
from omegakit.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
```

```yaml
dtype: ${dtype:float16}
use_cuda: ${cuda_available:}
```

`dtype` resolves to `torch.float16`, and `use_cuda` to `True` when PyTorch can use
CUDA on this machine.

## Rules

- `${dtype:<name>}` gives the `torch.dtype` named `<name>`, such as `float32` or
  `bfloat16`. A name that is not a dtype fails like any resolver error: reading it
  raises OmegaConf's `InterpolationResolutionError`, and validating or building
  raises `ConfigValidationError` ([Interpolation and missing values](../../guide/interpolation-and-missing/index.md#rules)).
- `${cuda_available:}` gives `torch.cuda.is_available()`.
- `register_torch_resolvers()` registers both. `register_torch_dtype_resolver()`
  and `register_cuda_available_resolver()` register one each.
- `register_torch_resolvers()` registers neither if either name is already
  registered, and raises `ValueError`, unless `replace=True`.
- Registering without PyTorch installed raises `ImportError`. Importing the module
  does not import PyTorch.
