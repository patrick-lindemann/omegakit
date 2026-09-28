# Imports

A string value that starts with `~import` is replaced by another YAML file, or by one
node of it. One file can hold the model sizes that experiments pick from:

```{literalinclude} models.yaml
:language: yaml
:caption: models.yaml
```

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: import_root
```

```text
{'hidden': 32, 'layers': 2}
```

`#small` selects the `small` node of the file, so `model` gets its keys and not a
`small:` key around them. Without `#`, the whole file is imported. A node path has
dots between keys and uses numbers for list items, counting from the end when
negative: `#small.hidden`, `#items.-1`.

The path is relative to the file that holds it, not to the working directory, so
the config loads from anywhere. Every import is an independent copy, so changing
one imported node never changes another import of the same file.

## Keeping imports inside a directory

By default an import may read any file the process can read. `import_root` limits
imports to one directory. `experiments/large.yaml` imports from its parent
directory, which is outside `experiments`:

```{literalinclude} experiments/large.yaml
:language: yaml
:caption: experiments/large.yaml
```

```{literalinclude} main.py
:language: python
:start-at: import_root
```

```text
32
Import `~import ../models.yaml#large` in `.../experiments/large.yaml` reads `.../models.yaml`, which is outside the import root `.../experiments`.
```

`omegakit check` and `omegakit show` take the same limit as `--import-root DIR`. It
is a limit, not a sandbox; see [Restricting imports](../../security/restricting-imports/index.md#rules).

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
- These raise `ConfigLoadError`, naming the statement and the importing
  file, with the original error as its `__cause__` where there is one: a file that
  does not exist, cannot be read or is invalid; a cycle; an
  interpolation in the path that fails; more than one `#`, so a file name with `#`
  cannot be imported; a `<node>` that does not exist, walks through a scalar or an
  interpolation, or has a bad or out-of-range index.
