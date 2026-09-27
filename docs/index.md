# omegakit

YAML configs that import and extend each other, and build your Python objects: one
file per environment, one base they share, and an optional dataclass schema that
checks the config before any configured object is built. omegakit is a library on
[OmegaConf](https://omegaconf.readthedocs.io/). You call `load_config`; it does not
take over your `main()`, your working directory or your logging.

```sh
pip install omegakit
```

Every example in these pages comes from one small web service, `webapp`. Its root
config names the class to build and picks an environment file, and the production
file takes the shared settings and replaces the database:

```{literalinclude} examples/webapp/configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

```{literalinclude} examples/webapp/configs/envs/prod.yaml
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
  [one config per environment](recipes/environments.md) or
  [swapping an implementation](recipes/swapping.md).
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

recipes/environments
recipes/swapping
recipes/manifests
recipes/tenants
```

```{toctree}
:caption: Contracts
:hidden:

contracts/command-line
contracts/errors
```

```{toctree}
:caption: Reference
:hidden:

api
changelog
```
