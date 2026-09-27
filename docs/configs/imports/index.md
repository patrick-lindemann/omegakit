# Imports

A string value that starts with `~import` is replaced by another YAML file, or by one
node of it. `curvefit` keeps the curves it can fit in one file:

```{literalinclude} ../../curvefit/configs/data/presets.yaml
:language: yaml
:caption: configs/data/presets.yaml
```

`base.yaml` imports one of them as the shared settings of its data splits
([Shared defaults](../shared-defaults/index.md)):

```{literalinclude} ../../curvefit/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:start-at: "data:"
:end-at: "$defaults:"
```

`#sine` selects the `sine` node of the file, so the splits get its keys and not a
`sine:` key around them. Without `#`, the whole file is imported. A node path has
dots between keys and uses numbers for list items, counting from the end when
negative: `#sine.function`, `#items.-1`.

An experiment on another curve imports the other node the same way:

```{literalinclude} cubic.yaml
:language: yaml
:caption: cubic.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: import_root
```

```text
curvefit.data.cubic 0.05
```

The path is relative to the file that holds it, not to the working directory. It
may contain interpolations, which see resolvers and the keys written in the same
file, because the rest of the config is not assembled yet.

Every import is an independent copy, so changing one imported node never changes
another import of the same file. Imports are replaced before any `$base` is merged,
which is why `$base: ~import ../base.yaml` works in the experiment files.

## Keeping imports inside a directory

By default an import may read any file the process can read. `import_root` limits
imports to one directory. `curvefit`'s experiments stay inside its `configs`
directory, and `cubic.yaml` reads from outside its own:

```{literalinclude} main.py
:language: python
:start-at: import_root
```

```text
['train', 'validation', 'test']
Import `~import ../../curvefit/configs/experiments/poly3-adam.yaml` in `.../configs/imports/cubic.yaml` reads `.../curvefit/configs/experiments/poly3-adam.yaml`, which is outside the import root `.../configs/imports`.
```

`omegakit check` and `omegakit show` take the same limit as `--import-root DIR`. It
is a limit, not a sandbox; see [Restricting imports](../../security/restricting-imports/index.md#import-root).

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
  symbolic links are resolved. The error names both paths. A `DIR` that does not exist raises
  `FileNotFoundError`, and a `DIR` that is a file `NotADirectoryError`. The root
  file is not checked. The default allows any file.
- These raise `ConfigValidationError`, naming the statement and the importing
  file, with the original error as its `__cause__` where there is one: a file that
  does not exist, cannot be read or is invalid; a cycle; an
  interpolation in the path that fails; more than one `#`, so a file name with `#`
  cannot be imported; a `<node>` that does not exist, walks through a scalar or an
  interpolation, or has a bad or out-of-range index.
