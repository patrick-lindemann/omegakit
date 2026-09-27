# Imports

A string value that starts with `~import` is replaced by another YAML file, or by one
node of it. `webapp` keeps its scheduled jobs in their own file and imports them
into the shared settings:

```{literalinclude} ../webapp/configs/jobs.yaml
:language: yaml
:caption: configs/jobs.yaml
```

```{literalinclude} ../webapp/configs/base.yaml
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

```{literalinclude} ../webapp/configs/app.yaml
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
imports to one directory:

```{literalinclude} imports/shared.yaml
:language: yaml
:caption: shared.yaml
```

```{literalinclude} imports/main.py
:language: python
:caption: main.py
```

```text
['digest', 'cleanup']
Import `~import ../../webapp/configs/base.yaml#server` in `.../guide/imports/shared.yaml` reads `.../webapp/configs/base.yaml`, which is outside the import root `.../guide/imports`.
```

`omegakit check` and `omegakit show` take the same limit as `--import-root DIR`. It
is a limit, not a sandbox; see [Security](../security.md#import-root).

## Rules

- Syntax: `~import <path>[#<node>]`. Whitespace around `<path>` and `<node>` is
  ignored. Only a string value that starts with `~import` is an import. Anywhere
  else in a string, `~import` is literal text.
- A relative `<path>` is relative to the importing file's directory. The path may
  contain `${…}`, which sees resolvers and the keys written in the importing file,
  not keys from a `$base`, another file or overrides.
- `<node>` is a dotted path from the imported file's root: keys in mappings,
  integer indices in lists, negative from the end (`#a.b.-1`). Empty means the
  whole file.
- An import can replace a mapping value or a list item. An imported file may hold
  a mapping or a list; the root file only a mapping. A file that holds a single
  value, such as `hello` or `5`, is rejected everywhere. An empty file, `null` or
  `~` is an empty mapping.
- Every import is an independent copy. Each file is read once per `load_config`.
- A file that imports itself, directly or through others, is a cycle. The same file
  imported from two branches is not.
- `import_root=DIR` rejects an import outside `DIR`, after interpolations and
  symbolic links are resolved. A `DIR` that does not exist raises
  `FileNotFoundError`, and a `DIR` that is a file `NotADirectoryError`. The root
  file is not checked. The default allows any file.
- These raise `ConfigValidationError`, naming the statement and the importing
  file: a file that does not exist, cannot be read or is invalid; a cycle; an
  interpolation in the path that fails; more than one `#`, so a file name with `#`
  cannot be imported; a `<node>` that does not exist, walks through a scalar or an
  interpolation, or has a bad or out-of-range index.
