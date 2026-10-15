# Torch

`omegakit.resolvers.torch` lets a config name PyTorch data types and devices, and
check for a GPU. PyTorch is not a dependency of omegakit: install it for your
platform first ([Overview](../overview/index.md#rules)). Here a config uses all
three resolvers:

```{literalinclude} precision.yaml
:language: yaml
:caption: precision.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

config.dtype: torch.bfloat16
config.device: cpu
config.use_cuda: False
model.weight.dtype: torch.bfloat16
ValidationInterpolationError: Cannot resolve the value: ValueError raised while resolving interpolation: Invalid torch dtype `bfloat`. (at `dtype`)
```

`${torch.dtype:bfloat16}` resolves to `torch.bfloat16`, the object itself, which
PyTorch accepts wherever it takes a `dtype`, and `${torch.device:cpu}` to
`torch.device("cpu")`. An override such as `'dtype=${torch.dtype:float32}'` picks
another type, and `bfloat`, which is no dtype, fails when the config is checked.

## Rules

- `${torch.dtype:<name>}` gives the attribute `torch.<name>` if it is a
  `torch.dtype`, such as `float32` or `bfloat16`. Any other name raises
  ``ValueError: Invalid torch dtype `<name>`.`` in the resolver: reading the value
  raises OmegaConf's `InterpolationResolutionError`, and `validate`, `instantiate`
  and `prepare` raise `ValidationInterpolationError`, as above
  ([Interpolation](../../guide/interpolation/index.md#rules)).
- `${torch.device:<name>}` gives `torch.device(<name>)`, such as `cpu` or `cuda:0`.
- `${torch.has_cuda:}` gives `torch.cuda.is_available()`.
- `register_torch_resolvers(*, replace=False, use_cache=True)` registers
  `torch.has_cuda`, `torch.device` and `torch.dtype`, in this order.
  `register_torch_cuda_resolver`, `register_torch_device_resolver` and
  `register_torch_dtype_resolver` register one each, with the same arguments
  ([Overview](../overview/index.md#rules)).
- Importing `omegakit.resolvers.torch` imports PyTorch, and raises `ImportError`
  without it.
