# Getting started

This page builds a curve-fitting experiment from a config in five steps. The
classes come from `curvefit`, the example package of these pages, and have nothing
omegakit-specific in them.

```sh
pip install omegakit
```

## 1. Build an object

A config file names the classes to build with `$class`. The other keys of the node
are the arguments:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:start-at: config = load_config("experiment.yaml")
:end-at: print(type(model)
```

```text
Polynomial 3
```

`load_config` returns an OmegaConf `DictConfig`, so everything OmegaConf offers
works on it. `instantiate` imports `curvefit.models.Polynomial` and calls it with
`degree=3`.

## 2. Fit the model

The data node is built the same way. `$ref` passes the function `sine` itself,
without calling it. `$partial: true` builds the optimizer later, because it needs
the model's parameters first:

```{literalinclude} main.py
:language: python
:start-at: random.seed(0)
:end-at: print(f"mse
```

```text
mse 0.0152
```

The model draws random initial coefficients, so the script seeds Python's
generator before building it. `curvefit`'s `SGD` and `Adam` take the same arguments
as `torch.optim.SGD` and `torch.optim.Adam`, in the same order, so moving to
PyTorch changes only `$class`.

## 3. Share a base

Experiments share most of their settings. `curvefit` keeps them in
`configs/base.yaml`: the seed, the data splits, the trainer and the metrics. Each
experiment file names that base and adds what differs:

```{literalinclude} ../curvefit/configs/experiments/linear-sgd.yaml
:language: yaml
:caption: configs/experiments/linear-sgd.yaml
```

`~import` reads another file, and `$base` merges it underneath the node, so the
experiment's own keys win. [Imports](../guide/imports/index.md) and
[Inheritance](../guide/inheritance/index.md) show how `base.yaml` is built.

## 4. Add a schema

A plain dataclass describes the whole experiment:

```{literalinclude} ../curvefit/curvefit/__init__.py
:language: python
:caption: curvefit/__init__.py (excerpt)
:start-at: "@dataclass"
```

`instantiate(config, schema=Experiment)` checks the config against it, then builds
every object and returns an `Experiment`:

```{literalinclude} main.py
:language: python
:start-at: config = load_config("configs/experiments/linear-sgd.yaml")
```

```text
linear-sgd Linear runs/linear-sgd/seed0
Unknown field(s) 'degre' in `model` (Polynomial). Expected one of: degree, init_scale.
```

A typo, or a value of the wrong type, raises `ConfigValidationError` before any
object is built. See [Validation](../schemas/validation/index.md).

## 5. Run an experiment

`curvefit`'s entrypoint does the same for one experiment file, trains the model
and writes its results to the run directory:

```{literalinclude} ../curvefit/main.py
:language: python
:caption: main.py
```

```text
$ python main.py configs/experiments/poly3-adam.yaml
poly3-adam: train loss 0.0416
test mse: 0.0377
test mae: 0.1589
```

[Reproducible runs](../reproducible-runs/index.md) explains what it saves and why.
From here, the guide covers each feature, starting with
[Loading](../guide/loading/index.md).
