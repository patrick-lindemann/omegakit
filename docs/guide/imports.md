# Imports

A string value that starts with `~import` is replaced by another YAML file, or by one
node of it.

## Example

```{literalinclude} ../examples/imports/models/encoder.yaml
:language: yaml
:caption: models/encoder.yaml
```

```{literalinclude} ../examples/imports/models/decoder.yaml
:language: yaml
:caption: models/decoder.yaml
```

```{literalinclude} ../examples/imports/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/imports/main.py
:language: python
:caption: main.py
```

## Rules

- The syntax is `~import <path>[#<node>]`. The path is relative to the importing
  file; an absolute path is used as is.
- `#<node>` selects a node by its dot-separated path. Segments on lists are indices,
  and negative indices count from the end: `#small.layers.0`, `#stages.-1`.
- An import can replace a mapping value or a list item, and the imported file may be
  a mapping or a list.
- Imports are resolved before `$base`, so `$base: ~import common.yaml` works.
- Every import is an independent copy. Changing one never changes another import of
  the same file.
- The path may contain interpolations, such as `~import models/${size}.yaml`. They
  see only the keys literally present in the importing file and registered
  resolvers.
- Importing the same file from two branches is fine. A file that imports itself,
  directly or through other files, is an error.

## Errors

| Problem | Exception |
|---|---|
| Circular import | `ValueError` (`Circular import detected`) |
| Missing file | `FileNotFoundError` |
| `#<node>` that does not exist, walks through a scalar or is out of range | `ValueError` (`selects node`) |
| More than one `#` | `ValueError` |

The full rules are in the [contracts](../contracts.md), section 7.
