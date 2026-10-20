# omegakit

omegakit is a small library on top of OmegaConf for experiment configs. Every
experiment is a YAML file in git that names its base and its includes by path. You
load it from your own `main()` and build your objects from it, checked before
anything is called. The same file and seed give the same run. Install it with
`pip install omegakit`, on Python 3.10 or newer.

```yaml
# base.yaml
$target: experiment.Experiment
seed: 0
epochs: 100
loss:
  $symbol: torch.nn.functional.mse_loss
optimizer:
  $target: torch.optim.SGD
  $partial: true
  lr: 0.1
```

```yaml
# linear.yaml
$base: ~include base.yaml
model:
  $target: torch.nn.Linear
  in_features: 16
  out_features: 1
```

```python
# experiment.py
from collections.abc import Callable
from dataclasses import dataclass

import torch


@dataclass
class Experiment:
    seed: int
    epochs: int
    loss: Callable[..., torch.Tensor]
    model: torch.nn.Module
    optimizer: Callable[..., torch.optim.Optimizer]
```

```python
# main.py
import torch
from experiment import Experiment
from omegakit import instantiate, load_config

config = load_config("linear.yaml")
torch.manual_seed(config.seed)
experiment = instantiate(config, Experiment)
model = experiment.model
optimizer = experiment.optimizer(model.parameters())
x, y = torch.randn(64, 16), torch.randn(64, 1)
for _ in range(experiment.epochs):
    optimizer.zero_grad()
    experiment.loss(model(x), y).backward()
    optimizer.step()
```

`linear.yaml` took the seed, the epochs, the loss and the optimizer from
`base.yaml`, and added a model. `$target` names a class or function to call, here
`Experiment` at the root, `$symbol` passes a function as it is, and `$partial`
builds the optimizer later, once the model's parameters exist. `instantiate` checks
the config against the fields of `Experiment` before anything is built:
`epochs: many` raises an error that names the key. The
[documentation](https://omegakit.readthedocs.io) trains a small PyTorch model in
every example.

## What you can do

- One file per experiment, sharing a base:
  [Getting started](https://omegakit.readthedocs.io/en/latest/getting-started/)
- Run one experiment for many values:
  [Parameter sweeps](https://omegakit.readthedocs.io/en/latest/recipes/parameter-sweeps/)
- Check configs before anything runs:
  [Validation](https://omegakit.readthedocs.io/en/latest/schemas/validation/)

omegakit does not launch jobs, parse your command line or record your runs. See
how it [compares with Hydra and other experiment tools](https://omegakit.readthedocs.io/en/latest/comparison/).

## Trust

Configs import and call Python code: loading one runs its resolvers, and
validating, checking and building one import the modules it names. Load configs
only from trusted sources, and wrap secrets in `${secret:...}`. The
[Trust model](https://omegakit.readthedocs.io/en/latest/security/trust-model/) page lists what
runs.

omegakit requires OmegaConf 2.4. It builds on OmegaConf but is not affiliated
with or endorsed by the OmegaConf project.
[Contributing](https://github.com/patrick-lindemann/omegakit/blob/main/CONTRIBUTING.md).
