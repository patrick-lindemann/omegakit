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

- **New to omegakit:** [Getting started](getting-started.md), and how omegakit
  [compares with Hydra and other libraries](comparison.md).
- **Looking up a feature:** the guide, from [Loading](guide/loading.md) and
  [Imports](guide/imports.md) to [Validation](guide/validation.md) and the
  [Command line](guide/command-line.md).
- **A complete pattern:** the recipes, such as
  [swapping an implementation](recipes/swapping.md) or
  [a manifest of similar things](recipes/manifests.md).
- **The exact rules:** the Rules section at the end of each guide page, and the
  [API](api.md).

Configs import and call Python code, so load them only from sources you trust.
[Security](security.md) lists what runs and how to log a config without its secrets.

```{toctree}
:hidden:

getting-started
comparison
```

```{toctree}
:caption: Guide
:hidden:

guide/loading
guide/imports
guide/base
guide/defaults
guide/overrides
guide/interpolation-and-missing
guide/building-objects
guide/typed-configs
guide/validation
guide/editor-schemas
guide/resolvers
guide/command-line
```

```{toctree}
:caption: Security
:hidden:

security
```

```{toctree}
:caption: Recipes
:hidden:

recipes/swapping
recipes/manifests
recipes/tenants
```

```{toctree}
:caption: Reference
:hidden:

api
errors
changelog
```
