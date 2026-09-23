# config-compose

Composable YAML configuration and Python object construction, powered by OmegaConf.
Requires Python 3.13 or newer. OmegaConf is the only runtime dependency.

```python
from config_compose import instantiate, load_config

config = load_config("app.yaml", overrides=["worker.timeout=30"])
worker = instantiate(config.worker)
```

```yaml
# defaults.yaml
timeout: 10
retries: 3
```

```yaml
# app.yaml
worker:
  $base: ~import defaults.yaml
  $class: myapp.Worker
  timeout: 20
```

## Configuration syntax

- `~import file.yaml` replaces a node with another file. Paths are relative to the
  importing file; `~import file.yaml#worker` selects a subnode. Cycles are rejected.
- `$base` merges a mapping or list of mappings underneath the current node. Later
  bases win over earlier bases; the current node wins over all bases.
- `$defaults` supplies defaults to dict-valued siblings. Item values win.
- `$class` imports and calls a Python class or callable with the node's arguments.
  Nested class nodes are instantiated recursively. A `from_config` method, if present,
  receives the materialized argument mapping instead of constructor keyword arguments.
- `$ref` imports an object without calling it. It is supported inside an instantiated
  tree and cannot have sibling arguments (except `$meta`).
- `$partial: true` returns a `functools.partial`. `prepare(config)` also defers the
  top-level call; nested objects are still built during preparation.
- `$meta` is removed by default; `load_config(..., keep_meta=True)` preserves it.
  Instantiation always ignores metadata. `keep_targets=False` removes construction keys.

Assembly runs imports, bases, and defaults, then applies overrides. Only structural
references are resolved during assembly; other interpolations stay lazy and resolve
against the assembled configuration. `???` can be filled by consumers and fails when
accessed or instantiated if still missing. Overrides accept dictionaries, DictConfig,
or OmegaConf `key=value` dotlists; they do not rerun structural assembly.

`Configurable` provides a default `from_config` implementation. `walk` traverses
mapping nodes depth-first, parents before children. The optional `type` argument to
`instantiate` and `prepare` is a typing hint, not runtime validation.

## Optional resolvers

Nothing is registered on import, and this library does not load `.env` files.

```python
from pathlib import Path
from config_compose.resolvers import register_paths_resolver

register_paths_resolver({"data_dir": Path("/srv/data")})
# YAML: dataset: ${paths:data_dir}/training
```

Paths are copied as strings; relative paths remain relative and unknown keys return
None. The caller defines the project layout.

```python
from config_compose.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
# YAML: dtype: ${dtype:float32}
# YAML: use_cuda: ${cuda_available:}
```

Install PyTorch separately for your platform before enabling these resolvers. It is
not a package dependency. Importing the resolver module does not import Torch;
registration without Torch raises an explanatory ImportError. Individual functions
`register_torch_dtype_resolver` and `register_cuda_available_resolver` are available.

Register resolvers before loading configs. Registration is global to OmegaConf and
refuses existing names unless `replace=True` is supplied. Resolver results are cached
per config; replacing a resolver does not clear caches on existing configs.

## Development

This directory is a member of the parent uv workspace and shares its lockfile.
From the repository root:

```sh
uv sync --package config-compose
uv run --package config-compose pytest -c workspace/config-compose/pyproject.toml --confcutdir=workspace/config-compose workspace/config-compose/tests
uv run --package config-compose ruff check workspace/config-compose
uv build --package config-compose
```

Workspace sync changes the shared environment. The package can also be copied into
its own repository and developed with `uv sync`, `uv run pytest`, and `uv build`.
Tests that require a real Torch installation skip when it is absent.

GraspDiff's original implementation and imports remain intact; migration is separate.
This package imports and calls Python objects specified by configs, so configs must
come from trusted sources. Assembly currently relies on private OmegaConf node APIs;
the supported OmegaConf range is intentionally constrained to 2.3.x.
