# omegakit

omegakit loads YAML configs that import and extend each other, and builds your
Python objects from them. Keep one file per environment on a shared base, name the
classes to build in the config, and add a dataclass schema that checks the config
before any object is built. It is a library on top of
[OmegaConf](https://omegaconf.readthedocs.io/). You call `load_config` from your
own `main()`, and omegakit does not touch your working directory or logging.

```sh
pip install omegakit
```

Every example in these pages comes from one small web service, `webapp`. Its root
config names the class to build and picks an environment file, and the production
file takes the shared settings and replaces the database:

```{literalinclude} webapp/configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

```{literalinclude} webapp/configs/envs/prod.yaml
:language: yaml
:caption: configs/envs/prod.yaml
```

```python
from omegakit import instantiate, load_config
from webapp import App

app = instantiate(load_config("configs/app.yaml"), App)  # with APP_ENV=prod
```

## Where to go

- **New to omegakit:** [Getting started](getting-started/index.md), and how omegakit
  [compares with Hydra and other libraries](comparison/index.md).
- **Looking up a feature:** the guide, from [Loading](guide/loading/index.md) and
  [Imports](guide/imports/index.md) to [Validation](guide/validation/index.md) and the
  [Command line](guide/command-line/index.md).
- **A complete pattern:** the recipes, such as
  [swapping an implementation](recipes/swapping/index.md) or
  [a manifest of similar things](recipes/manifests/index.md).
- **The exact rules:** the Rules section at the end of each guide page, and the
  [API](api/index.md).

Configs import and call Python code, so load them only from sources you trust.
The Security section says [what runs](security/what-runs/index.md), how to
[limit it](security/limits/index.md) and how to log a config
[without its secrets](security/secrets/index.md).

```{toctree}
:hidden:

getting-started/index
comparison/index
```

```{toctree}
:caption: Guide
:hidden:

guide/loading/index
guide/imports/index
guide/base/index
guide/defaults/index
guide/overrides/index
guide/interpolation-and-missing/index
guide/building-objects/index
guide/typed-configs/index
guide/validation/index
guide/editor-schemas/index
guide/command-line/index
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

security/what-runs/index
security/limits/index
security/secrets/index
```

```{toctree}
:caption: Recipes
:hidden:

recipes/swapping/index
recipes/manifests/index
recipes/tenants/index
recipes/sweeps/index
```

```{toctree}
:caption: Reference
:hidden:

api/index
changelog/index
```
