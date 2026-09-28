# Getting started

This page trains a small PyTorch model from a config in five steps. It fits a
multilayer perceptron to noisy samples of a sine wave. The classes come from
`project.py`, the example project of these pages: `project.MLP` is a PyTorch module
with `layers` hidden layers of `hidden` units, and `project.SineWave` a PyTorch
`Dataset` of `n` noisy samples of `sin(x)`.

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
:end-at: print("model:"
```

```{code-block} text
:caption: Output

model: MLP(
  (net): Sequential(
    (0): Linear(in_features=1, out_features=32, bias=True)
    (1): Tanh()
    (2): Linear(in_features=32, out_features=32, bias=True)
    (3): Tanh()
    (4): Linear(in_features=32, out_features=1, bias=True)
  )
)
```

`instantiate` imports `project.MLP` and calls it with `hidden=32`. Any class works
the same, such as `torch.nn.Linear`.

## 2. Train the model

The dataset is built the same way. `$partial: true` builds the optimizer as a
`functools.partial`, which the code calls with the model's parameters
([Instantiation](../objects/instantiation/index.md)):

```{literalinclude} main.py
:language: python
:start-at: import torch
:end-at: print("loss:"
```

```{code-block} text
:caption: Output

loss: 0.012
```

The training loop is plain PyTorch.

## 3. Share a base

Experiments share most of their settings. The example project keeps them in a base
file:

```{literalinclude} ../example/configs/base.yaml
:language: yaml
:caption: configs/base.yaml
```

Each experiment file names that base and adds what differs:

```{literalinclude} ../example/configs/experiments/mlp.yaml
:language: yaml
:caption: configs/experiments/mlp.yaml
```

`~import` reads another file, and `$base` merges it underneath the node, so the
experiment's own keys win ([Imports](../guide/imports/index.md),
[Inheritance](../guide/inheritance/index.md)). `name: ???` is a value each
experiment must set ([Missing values](../guide/missing-values/index.md)), and
`${seed}` refers to another value ([Interpolation](../guide/interpolation/index.md)).

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
every object and returns an `Experiment`. Its `loss` is
`$ref: torch.nn.functional.mse_loss` in `base.yaml`, the function itself. A typo, or
a value of the wrong type, raises `ConfigValidationError` before any object is
built:

```{literalinclude} main.py
:language: python
:start-at: from project import
```

```{code-block} text
:caption: Output

error: Unknown field(s) 'hiden' in `model` (MLPConfig). Expected one of: hidden, layers, activation.
```

## 5. Run an experiment

The project's entrypoint does the same for one experiment file and the overrides it
is given. It seeds PyTorch before building, because the model draws random initial
weights, trains the model, and saves the config and the weights to the run
directory:

```{literalinclude} ../example/main.py
:language: python
:caption: main.py
```

```text
$ python main.py configs/experiments/mlp.yaml
mlp: test loss 0.011
```

The saved `config.yaml` loads like any config file, so
`python main.py runs/mlp/seed0/config.yaml run_dir=runs/repeat` repeats the run.
From here, the Guide covers each feature, starting with
[Loading](../guide/loading/index.md).
