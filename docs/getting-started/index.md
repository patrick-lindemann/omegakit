# Getting started

This page trains a small PyTorch model from a config in five steps. It fits a
multilayer perceptron to noisy samples of a sine wave. The model, the dataset and
the experiment come from `project.py`, the example project of these pages, and have
nothing omegakit-specific in them.

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
MLP 1153
```

`load_config` returns an OmegaConf `DictConfig`, so everything OmegaConf offers
works on it. `instantiate` imports `project.MLP` and calls it with `hidden=32`. Any
class works the same, such as `torch.nn.Linear`.

## 2. Train the model

The dataset is built the same way. The optimizer needs the model's parameters,
which exist only once the model is built, so `$partial: true` builds a
`functools.partial` of `torch.optim.Adam`, which the code calls with them:

```{literalinclude} main.py
:language: python
:start-at: torch.manual_seed(0)
:end-at: print(f"loss
```

```text
loss 0.012
```

The model draws random initial weights, so the script seeds PyTorch before building
it. The training loop is plain PyTorch.

## 3. Share a base

Experiments share most of their settings. The example project keeps them in
`configs/base.yaml`: the seed, the data splits, the loss and the number of epochs.
Each experiment file names that base and adds what differs:

```{literalinclude} ../example/configs/experiments/mlp.yaml
:language: yaml
:caption: configs/experiments/mlp.yaml
```

`~import` reads another file, and `$base` merges it underneath the node, so the
experiment's own keys win. [Imports](../guide/imports/index.md) and
[Inheritance](../guide/inheritance/index.md) explain both.

## 4. Add a schema

A plain dataclass describes the whole experiment:

```{literalinclude} ../example/project.py
:language: python
:caption: project.py (excerpt)
:start-after: "    test: Dataset"
:end-at: "batch_size: int = 32"
:lines: 3-
```

`instantiate(config, schema=Experiment)` checks the config against it, then builds
every object and returns an `Experiment`. In `base.yaml`, `loss` is
`$ref: torch.nn.functional.mse_loss`, which passes the function itself without
calling it:

```{literalinclude} main.py
:language: python
:start-at: config = load_config("configs/experiments/linear.yaml")
```

```text
linear Linear runs/linear/seed0
Unknown field(s) 'hiden' in `model` (MLPConfig). Expected one of: hidden, layers, activation.
```

A typo, or a value of the wrong type, raises `ConfigValidationError` before any
object is built. See [Validation](../schemas/validation/index.md).

## 5. Run an experiment

The project's entrypoint does the same for one experiment file, trains the model
and writes its results to the run directory:

```{literalinclude} ../example/main.py
:language: python
:caption: main.py
```

```text
$ python main.py configs/experiments/mlp.yaml
mlp: test loss 0.011
```

[Reproducible runs](../reproducible-runs/index.md) explains what it saves and why.
From here, the Guide covers each feature, starting with
[Loading](../guide/loading/index.md).
