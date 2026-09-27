# Torch

`omegakit.resolvers.torch` lets a config name PyTorch data types and check for a
GPU. PyTorch is not a dependency of omegakit: install it for your platform first
([Overview](../overview/index.md#resolvers-for-other-libraries)).

The PyTorch variant of `curvefit` registers the resolvers before it loads its
config:

```{literalinclude} ../../curvefit/torch/main.py
:language: python
:caption: torch/main.py (excerpt)
:lines: 9-12
```

```{literalinclude} ../../curvefit/torch/experiment.yaml
:language: yaml
:caption: torch/experiment.yaml
```

`${dtype:float32}` resolves to `torch.float32`, which the model receives as its
`dtype`. An override picks another type, from `curvefit`'s directory:

```text
$ PYTHONPATH=. python torch/main.py 'model.dtype=${dtype:bfloat16}'
poly3-adam-torch: Adam, torch.bfloat16
train loss 0.04
test mse: 0.04
test mae: 0.16
```

`${cuda_available:}` resolves to `True` when PyTorch can use CUDA on this machine,
for a config that chooses its device.

## Rules

- `${dtype:<name>}` gives the `torch.dtype` named `<name>`, such as `float32` or
  `bfloat16`. A name that is not a dtype fails like any resolver error: reading it
  raises OmegaConf's `InterpolationResolutionError`, and validating or building
  raises `ConfigValidationError` ([Interpolation](../../configs/interpolation/index.md#rules)).
- `${cuda_available:}` gives `torch.cuda.is_available()`.
- `register_torch_resolvers()` registers both. `register_torch_dtype_resolver()`
  and `register_cuda_available_resolver()` register one each.
- `register_torch_resolvers()` registers neither if either name is already
  registered, and raises `ValueError`, unless `replace=True`.
- Registering without PyTorch installed raises `ImportError`. Importing the module
  does not import PyTorch.
