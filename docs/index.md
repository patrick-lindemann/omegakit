# omegakit

omegakit is a small library on top of [OmegaConf](https://omegaconf.readthedocs.io/)
for experiment configs. Every experiment is a YAML file in git that names its base
and its imports by path. You load it from your own `main()`, check it against a
dataclass, and build your objects from it. The same file and seed give the same run.
It was developed for machine learning, but nothing in it is specific to that.

```sh
pip install omegakit
```

Every example in these pages comes from `curvefit`, a small experiment in plain
Python that fits a curve to noisy samples of a known function. One experiment file
names its base, the model and the optimizer:

```{literalinclude} curvefit/configs/experiments/poly3-adam.yaml
:language: yaml
:caption: configs/experiments/poly3-adam.yaml
```

```python
from curvefit import Experiment
from omegakit import instantiate, load_config

config = load_config("configs/experiments/poly3-adam.yaml")
experiment = instantiate(config, schema=Experiment)
```

## Where to go

- **New to omegakit:** [Getting started](getting-started/index.md),
  [Reproducible runs](reproducible-runs/index.md), and how omegakit
  [compares with Hydra and other libraries](comparison/index.md).
- **Looking up a feature:** one page per feature, in the order you meet them.
  [Configs](configs/loading/index.md) covers how files are loaded and combined,
  [Schemas](schemas/dataclass-schemas/index.md) how a config is checked, and
  [Building objects](objects/instantiation/index.md) how objects are built from it.
- **A complete pattern:** the recipes, such as
  [Parameter sweeps](recipes/parameter-sweeps/index.md) or
  [Swapping implementations](recipes/swapping-implementations/index.md).
- **The exact rules:** the Rules section at the end of each feature page, and the
  [API](api/index.md).

Configs import and call Python code, so load them only from sources you trust.
The Security section says [what runs](security/trust-model/index.md), how to
[limit it](security/restricting-imports/index.md) and how to keep
[secrets](security/secrets/index.md) out of saved configs and logs.

```{toctree}
:hidden:

getting-started/index
reproducible-runs/index
command-line/index
handling-errors/index
comparison/index
```

```{toctree}
:caption: Configs
:hidden:

configs/loading/index
configs/imports/index
configs/inheritance/index
configs/shared-defaults/index
configs/overrides/index
configs/interpolation/index
configs/environment-variables/index
configs/missing-values/index
```

```{toctree}
:caption: Schemas
:hidden:

schemas/dataclass-schemas/index
schemas/validation/index
schemas/editor-support/index
```

```{toctree}
:caption: Building objects
:hidden:

objects/instantiation/index
objects/configurable-classes/index
```

```{toctree}
:caption: Resolvers
:hidden:

resolvers/overview/index
resolvers/paths/index
resolvers/torch/index
```

```{toctree}
:caption: Security
:hidden:

security/trust-model/index
security/restricting-imports/index
security/secrets/index
```

```{toctree}
:caption: Recipes
:hidden:

recipes/parameter-sweeps/index
recipes/swapping-implementations/index
recipes/using-with-pytorch/index
recipes/checking-experiments-in-ci/index
```

```{toctree}
:caption: Reference
:hidden:

api/index
changelog/index
```
