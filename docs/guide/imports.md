# Imports

A string value that starts with `~import` is replaced by another YAML file, or by one
node of it. `webapp` keeps its scheduled jobs in their own file and imports them
into the shared settings:

```{literalinclude} ../examples/webapp/configs/jobs.yaml
:language: yaml
:caption: configs/jobs.yaml
```

```{literalinclude} ../examples/webapp/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:start-at: "jobs:"
:end-at: "jobs:"
```

`#jobs` selects the `jobs` node of the file, so `base.yaml` gets the two jobs and
not a `jobs:` key around them. Without `#`, the whole file is imported. A node path
has dots between keys and uses numbers for list items, counting from the end when
negative: `#jobs.digest`, `#hosts.-1`.

The path is relative to the file that holds it, and may contain interpolations. The
root file uses one to pick the environment:

```{literalinclude} ../examples/webapp/configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

`${oc.env:APP_ENV,dev}` reads the `APP_ENV` environment variable, with `dev` as the
default. An interpolation in an import path sees resolvers and the keys written in
the same file, because the rest of the config is not assembled yet.

Every import is an independent copy, so changing one imported node never changes
another import of the same file. Imports are replaced before any `$base` is merged,
which is why `$base: ~import ../base.yaml` works in the environment files.

## Keeping imports inside a directory

By default an import may read any file the process can read. `import_root` limits
imports to one directory, after interpolations and symbolic links are resolved:

```{literalinclude} ../examples/guide/imports/shared.yaml
:language: yaml
:caption: shared.yaml
```

```{literalinclude} ../examples/guide/imports/main.py
:language: python
:caption: main.py
```

```text
['digest', 'cleanup']
Import `~import ../../webapp/configs/base.yaml#server` in `.../guide/imports/shared.yaml` reads `.../webapp/configs/base.yaml`, which is outside the import root `.../guide/imports`.
```

`omegakit check` and `omegakit show` take the same limit as `--import-root DIR`.

An import of a file that does not exist raises `ConfigValidationError`, naming the
statement and the importing file. The full rules, including cycles and node paths
that do not exist, are in the contracts under
[Imports](../contracts/assembly.md#imports).
