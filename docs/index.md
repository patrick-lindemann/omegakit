# omegakit

Composable YAML configuration and Python object construction, built on
[OmegaConf](https://omegaconf.readthedocs.io/).

- **Compose** configs from files: `~import` another file or one of its nodes, merge
  shared settings with `$base`, and give every item of a mapping the same defaults
  with `$defaults`.
- **Construct** objects from them: `$class` builds a class or calls a function,
  `$ref` imports an object, and `$partial` defers the call.
- **Check** them: dataclass schemas validate configs before anything is built, and
  the same schemas give YAML editors completion and error highlighting.

```sh
pip install omegakit
```

## Quickstart

```{literalinclude} examples/getting-started/defaults.yaml
:language: yaml
:caption: defaults.yaml
```

```{literalinclude} examples/getting-started/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} examples/getting-started/main.py
:language: python
:caption: main.py
```

Continue with [Getting started](getting-started.md), or look up a feature in the
guide.

```{toctree}
:hidden:

getting-started
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
guide/instantiation
guide/configurable
guide/typed-configs
guide/validation
guide/editor-schemas
guide/metadata
guide/resolvers
guide/walk
```

```{toctree}
:caption: Recipes
:hidden:

cookbook
```

```{toctree}
:caption: Reference
:hidden:

contracts
api
changelog
```
