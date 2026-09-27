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
- **Looking up a feature:** one page per feature, in the order you meet them.
  [Configs](configs/loading/index.md) covers how files are loaded and combined,
  [Building objects](objects/instantiation/index.md) how objects are built and checked,
  and [Tools](tools/command-line/index.md) the command line and editor support.
- **A complete pattern:** the recipes, such as
  [Swapping implementations](recipes/swapping-implementations/index.md) or
  [Parameter sweeps](recipes/parameter-sweeps/index.md).
- **The exact rules:** the Rules section at the end of each feature page, and the
  [API](api/index.md).

Configs import and call Python code, so load them only from sources you trust.
The Security section says [what runs](security/trust-model/index.md), how to
[limit it](security/restricting-imports/index.md) and how to log a config
[without its secrets](security/masking-secrets/index.md).

```{toctree}
:hidden:

getting-started/index
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
:caption: Building objects
:hidden:

objects/instantiation/index
objects/schemas/index
objects/validation/index
```

```{toctree}
:caption: Tools
:hidden:

tools/command-line/index
tools/editor-support/index
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
security/masking-secrets/index
```

```{toctree}
:caption: Recipes
:hidden:

recipes/swapping-implementations/index
recipes/manifests/index
recipes/per-tenant-configs/index
recipes/parameter-sweeps/index
```

```{toctree}
:caption: Reference
:hidden:

api/index
changelog/index
```
