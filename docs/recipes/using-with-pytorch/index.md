# Using with PyTorch

`curvefit`'s `SGD` and `Adam` take the same arguments as `torch.optim.SGD` and
`torch.optim.Adam`, so an experiment moves to PyTorch by changing classes, not
settings. The PyTorch variant of `curvefit` bases its config on `poly3-adam.yaml`:

```{literalinclude} ../../curvefit/torch/experiment.yaml
:language: yaml
:caption: torch/experiment.yaml
```

The optimizer keeps its `$partial` and its learning rate, and changes only `$class`.
The model becomes a PyTorch module, which subclasses `curvefit`'s `Model` as well,
so the `model: Model` field of `Experiment` accepts it:

```{literalinclude} ../../curvefit/torch/torch_models.py
:language: python
:caption: torch/torch_models.py
```

The entrypoint registers the [Torch resolvers](../../resolvers/torch/index.md) for
`${dtype:...}`, and seeds PyTorch's generator as well as Python's, because the
model draws its initial coefficients with `torch.randn`:

```{literalinclude} ../../curvefit/torch/main.py
:language: python
:caption: torch/main.py (excerpt)
:lines: 11-16
```

From `curvefit`'s directory:

```text
$ PYTHONPATH=. python torch/main.py
poly3-adam-torch: Adam, torch.float32
train loss 0.03
test mse: 0.03
test mae: 0.14
```

`torch.optim.Adam` has no schema, so PyTorch checks its arguments when the partial
is called. To limit what the config can name, allow the PyTorch optimizers next to
your own modules: `allowed_modules=["curvefit", "torch_models", "torch.optim"]`
([Restricting imports](../../security/restricting-imports/index.md)). Setting
PyTorch's determinism flags stays with you
([Reproducible runs](../../reproducible-runs/index.md#what-omegakit-does-not-do)).
