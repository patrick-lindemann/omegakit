# Getting started

This page trains a small PyTorch model from a config in five steps. It fits a
multilayer perceptron to noisy samples of a sine wave. The classes come from
`project.py`, the example project of these pages: `project.MLP` is a PyTorch module
with `layers` hidden layers of `hidden` units, and `project.SineWave` a PyTorch
`Dataset` of `n` noisy samples of `sin(x)`.

omegakit needs Python 3.12 or newer and OmegaConf 2.4:

```sh
pip install omegakit
```

## 1. Build an object

A config file names the class to build with `$target`. The other keys of the node
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

`~include` reads another file, and `$base` merges it underneath the node, so the
experiment's own keys win ([Includes](../guide/includes/index.md),
[Inheritance](../guide/inheritance/index.md)). `name: ???` is a value each
experiment must set ([Missing values](../guide/missing-values/index.md)), and
`${seed}` refers to another value ([Interpolation](../guide/interpolation/index.md)).

## 4. Build the whole experiment

The root of `base.yaml` names the dataclass `Experiment` with `$target`, so the
whole experiment is one object. The datasets are grouped by the `TypedDict`
`DataConfig`, a schema that only checks its keys
([TypedDict schemas](../schemas/typed-dict-schemas/index.md)):

```{literalinclude} ../example/project.py
:language: python
:caption: project.py (excerpt)
:start-at: "class DataConfig"
:end-at: "batch_size: int = 32"
```

`instantiate(config, Experiment)` checks the config against the fields of
`Experiment`, then builds every `$target` node and returns an `Experiment`. Its
`data` is a `dict` with the two datasets, and its `loss` is
`$symbol: torch.nn.functional.mse_loss` in `base.yaml`, the function itself. `MLP`
names its own schema, `MLPConfig`
([Configurable classes](../objects/configurable-classes/index.md)), so a typo or a
value of the wrong type raises a `ConfigValidationError` before any object is
built:

```{literalinclude} main.py
:language: python
:start-at: from project import
```

```{code-block} text
:caption: Output

ConfigSchemaError: `hiden` is not a field of `MLPConfig`. Its fields are `hidden`, `layers`, `activation`. (at `model`)
```

## 5. Run an experiment

The project's entrypoint does the same for one experiment file and the overrides it
is given. It seeds PyTorch before building, because the model draws random initial
weights, trains the model, and saves the config, the overrides and the weights to
the run directory:

```{literalinclude} ../example/main.py
:language: python
:caption: main.py
```

```sh
python main.py configs/experiments/mlp.yaml
```

```{code-block} text
:caption: Output

mlp: test loss 0.011
```

The saved `config.yaml` loads like any config file, so it repeats the run. The
override gives the repeat a directory of its own, since `main.py` never writes
into an existing one:

```sh
python main.py runs/mlp/seed0/config.yaml run_dir=runs/repeat
```

```{code-block} text
:caption: Output

mlp: test loss 0.011
```

From here, the Guide covers each feature, starting with
[Loading](../guide/loading/index.md).
