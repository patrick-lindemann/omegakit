# Loading

`load_config` reads a YAML file and assembles it into an OmegaConf `DictConfig`.
The `webapp` root file is two lines, and everything else arrives while loading:

```{literalinclude} ../examples/webapp/configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

```{literalinclude} ../examples/guide/loading/main.py
:language: python
:caption: main.py
:end-before: keep_meta
```

```text
9000
webapp.db.SQLite
```

The `$base` line pulled in `envs/dev.yaml`, which pulled in `base.yaml`, and the
override set the port last. Paths in `~import` are relative to the file that holds
them, not to the working directory, so the config loads from anywhere.

## The order of assembly

1. Every `~import` is replaced by the file or node it names ([Imports](imports.md)).
2. Every `$base` is merged underneath its node ([Base](base.md)).
3. Every `$defaults` is merged under its siblings ([Defaults](defaults.md)).
4. The overrides are merged on top
   ([Overrides and environment variables](overrides.md)).
5. `$meta` is removed, unless you pass `keep_meta=True`.

The order explains what works together:

- `$base: ~import base.yaml` works, because the import has already replaced the
  string when bases are merged.
- A `$defaults` that arrives through a `$base` or an `~import` works, because
  defaults are applied after all bases.
- An override cannot add an `~import`, a `$base` or a `$defaults`: it arrives after
  assembly, so those stay literal.

Every other `${…}` stays unresolved until a value is read or built
([Interpolation and missing values](interpolation-and-missing.md)).

## Metadata and plain data

`$meta` holds notes for people and tools, such as who owns a job. It is removed
while loading unless you ask for it, and never reaches a constructor. `walk` visits
every mapping of a config, parents first, so a script can collect it:

```{literalinclude} ../examples/guide/loading/main.py
:language: python
:start-at: keep_meta
```

```text
webapp.jobs.Job growth
```

`keep_targets=False` removes `$class`, `$ref` and `$partial` instead, which leaves
plain data for code that builds nothing.

A file that is not valid YAML, or an import that fails, raises
`ConfigValidationError` naming the file and the line. The full order is in the
contracts under [Pipeline](../contracts.md#pipeline).
