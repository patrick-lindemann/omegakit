# omegakit

omegakit is a small library on top of OmegaConf for experiment configs. Every
experiment is a YAML file in git that names its base and its imports by path. You
load it from your own `main()`, check it against a dataclass, and build your objects
from it. The same file and seed give the same run. Install it with
`pip install omegakit`, on Python 3.12 or newer.

```yaml
# base.yaml
seed: 0
data:
  $class: curvefit.data.Synthetic
  function:
    $ref: curvefit.data.sine
  noise: 0.1
  n: 200
  seed: ${seed}
optimizer:
  $class: curvefit.optim.SGD
  $partial: true
  lr: 0.1
```

```yaml
# poly3.yaml
$base: ~import base.yaml
model:
  $class: curvefit.models.Polynomial
  degree: 3
```

```python
from collections.abc import Callable
from dataclasses import dataclass

from curvefit.data import Dataset
from curvefit.models import Model
from curvefit.optim import Optimizer
from omegakit import instantiate, load_config


@dataclass
class Experiment:
    seed: int
    data: Dataset
    model: Model
    optimizer: Callable[..., Optimizer]


experiment = instantiate(load_config("poly3.yaml"), schema=Experiment)
```

`poly3.yaml` took the seed, the data and the optimizer from `base.yaml`, and added
a model. `$class` names a class to build, `$ref` passes a function as it is, and
`$partial` builds the optimizer later, once the model's parameters exist. The
dataclass, and the dataclasses that `$class` names, check the config before
anything is built: `degree: three` raises an error that names the key. `curvefit` is
the example experiment of the [documentation](https://omegakit.readthedocs.io).

## What you can do

- One file per experiment, sharing a base:
  [Getting started](https://omegakit.readthedocs.io/en/latest/getting-started/)
- Save a run's config and repeat the run:
  [Reproducible runs](https://omegakit.readthedocs.io/en/latest/reproducible-runs/)
- Run one experiment for many values:
  [Parameter sweeps](https://omegakit.readthedocs.io/en/latest/recipes/parameter-sweeps/)
- Check configs before anything runs, and get completion in your editor:
  [Validation](https://omegakit.readthedocs.io/en/latest/schemas/validation/),
  [Editor support](https://omegakit.readthedocs.io/en/latest/schemas/editor-support/)
- Move an experiment to PyTorch:
  [Using with PyTorch](https://omegakit.readthedocs.io/en/latest/recipes/using-with-pytorch/)

omegakit does not launch jobs, parse your command line or record your runs. See
how it [compares with Hydra and other experiment tools](https://omegakit.readthedocs.io/en/latest/comparison/).

## Trust

Configs import and call Python code: loading one runs its resolvers, and
validating, checking and building one import the modules it names. Load configs
only from trusted sources, and read secrets with `${secret:NAME}`. The
[Trust model](https://omegakit.readthedocs.io/en/latest/security/trust-model/) page lists what
runs.

omegakit supports OmegaConf 2.3 and 2.4. It builds on OmegaConf but is not affiliated
with or endorsed by the OmegaConf project.
[Contributing](https://github.com/patrick-lindemann/omegakit/blob/main/CONTRIBUTING.md).
