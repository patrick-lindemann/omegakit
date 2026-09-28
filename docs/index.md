# omegakit

omegakit is a small library on top of [OmegaConf](https://omegaconf.readthedocs.io/)
for experiment configs. Every experiment is a YAML file in git that names its base
and its imports by path. You load it from your own `main()`, check it against a
dataclass, and build your objects from it. The same file and seed give the same run.
It was developed for machine learning, but nothing in it is specific to that. The
examples in these pages train a small PyTorch model.

## Where to go

- **New to omegakit:** [Getting started](getting-started/index.md) installs it and
  trains a model from a config, and [Comparison](comparison/index.md) sets omegakit
  against Hydra and other libraries.
- **Looking up a feature:** one page per feature, in the order you meet them.
  The [Guide](guide/loading/index.md) covers how files are loaded and combined,
  [Building objects](objects/instantiation/index.md) how objects are built from
  them, and [Schemas](schemas/dataclass-schemas/index.md) how a config is checked.
- **A complete pattern:** the recipes, such as
  [Parameter sweeps](recipes/parameter-sweeps/index.md) or
  [Swapping implementations](recipes/swapping-implementations/index.md).
- **From a terminal:** the [command line](command-line/index.md) checks and prints
  configs without a script.
- **Reference:** the Rules section at the end of each feature page, and the
  [API](api/index.md).

Configs import and call Python code, so load them only from sources you trust.
The Security section says [what runs](security/trust-model/index.md), how to
[limit it](security/restricting-imports/index.md) and how to keep
[secrets](security/secrets/index.md) out of saved configs and logs.

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
guide/inheritance/index
guide/defaults/index
guide/overrides/index
guide/interpolation/index
guide/environment-variables/index
guide/missing-values/index
guide/metadata/index
guide/errors/index
```

```{toctree}
:caption: Building objects
:hidden:

objects/instantiation/index
objects/configurable-classes/index
```

```{toctree}
:caption: Schemas
:hidden:

schemas/dataclass-schemas/index
schemas/validation/index
schemas/editor-support/index
```

```{toctree}
:caption: Resolvers
:hidden:

resolvers/overview/index
resolvers/paths/index
resolvers/torch/index
```

```{toctree}
:caption: Command line
:hidden:

command-line/index
command-line/check/index
command-line/show/index
command-line/export-schema/index
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
recipes/checking-experiments-in-ci/index
```

```{toctree}
:caption: Reference
:hidden:

api/index
changelog/index
```
