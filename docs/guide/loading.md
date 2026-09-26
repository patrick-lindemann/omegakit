# Loading

`load_config(path)` reads a YAML file and assembles it into an OmegaConf
`DictConfig`. Assembly runs in a fixed order:

1. Resolve every `~import` ([Imports](imports.md)).
2. Merge every `$base` ([Base](base.md)).
3. Apply every `$defaults` ([Defaults](defaults.md)).
4. Merge the `overrides` ([Overrides](overrides.md)).
5. Strip `$meta`, and optionally the construction keys.

Other interpolations stay lazy: they resolve when a value is read or instantiated
([Interpolation and `???`](interpolation-and-missing.md)).

## Example

```{literalinclude} ../examples/loading/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/loading/main.py
:language: python
:caption: main.py
```

## Options

- `overrides`: values merged last, as a list of `key=value` strings, a `dict` or a
  `DictConfig`.
- `keep_meta=True` keeps the `$meta` keys ([Metadata](metadata.md)).
- `keep_targets=False` removes `$class`, `$ref` and `$partial`, which leaves plain
  data for code that does not instantiate anything.

The path may be a `str` or a `Path`. Paths in `~import` are relative to the file
that contains them, not to the working directory.

## Errors

| Problem | Exception |
|---|---|
| The file, or an imported file, does not exist | `FileNotFoundError` |
| A malformed import, `$base` or `$defaults` | `ValueError`, naming the node |
| Overrides of another type | `ValueError` (`Unsupported overrides type`) |

Unknown `$` keys are kept by `load_config`; `instantiate` rejects them. The complete
order and its consequences are in the [contracts](../contracts.md), section 1.
