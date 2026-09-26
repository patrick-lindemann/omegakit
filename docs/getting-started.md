# Getting started

This page builds a small application config step by step. Each step links to the
guide page that covers it in full.

## Install

```sh
pip install omegakit
```

omegakit needs Python 3.12 or newer. Its only dependencies are OmegaConf 2.3 and
typing_extensions.

## A class to build

Configs describe objects. Here is a plain class, with nothing omegakit-specific in
it:

```{literalinclude} examples/getting-started/app.py
:language: python
:caption: app.py
```

## Two config files

Shared settings go into their own file:

```{literalinclude} examples/getting-started/defaults.yaml
:language: yaml
:caption: defaults.yaml
```

The application config builds on it:

```{literalinclude} examples/getting-started/app.yaml
:language: yaml
:caption: app.yaml
```

- `~import defaults.yaml` replaces the value with the content of that file. The path
  is relative to the importing file. See [Imports](guide/imports.md).
- `$base` merges the imported mapping underneath `worker`, so `worker`'s own
  `timeout: 20` wins over the shared `timeout: 10`. See [Base](guide/base.md).
- `$class: app.Worker` names the class to build, by its import path. See
  [Instantiation](guide/instantiation.md).

## Load and build

```{literalinclude} examples/getting-started/main.py
:language: python
:caption: main.py
```

- `load_config` reads the file and assembles it: imports, bases, defaults, then the
  overrides. The result is an OmegaConf `DictConfig`. See [Loading](guide/loading.md).
- `overrides=["worker.retries=5"]` changes a value, as a command line would. See
  [Overrides](guide/overrides.md).
- `instantiate` calls `app.Worker` with the node's other keys as arguments. The
  second argument, `Worker`, is only a type hint for your editor and type checker.

## Next steps

- Give the class a dataclass schema, so configs are checked before anything is
  built: [Typed configs](guide/typed-configs.md) and [Validation](guide/validation.md).
- Get completion and error highlighting in YAML files:
  [Editor schemas](guide/editor-schemas.md).
- See complete patterns in the [Cookbook](cookbook.md).

Configs import and call Python objects, so load them only from trusted sources.
