# Overrides

Overrides change values after a config is assembled. They are the strongest source of
values, and the usual way to pass command-line settings.

## Example

```{literalinclude} ../examples/overrides/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/overrides/main.py
:language: python
:caption: main.py
```

## Forms

- A list of `key=value` strings (an OmegaConf dotlist), such as `sys.argv[1:]`.
  Values are parsed as YAML, so `seed=42` is an integer.
- A nested `dict` or a `DictConfig`, merged like a `$base` on top.

`load_config(..., overrides=...)` merges them into the loaded config.
`instantiate(..., overrides=...)` and `prepare(..., overrides=...)` merge them into a
copy of the node being built; the config passed in is not changed.

## Rules

- Overrides arrive after assembly. `~import`, `$base` and `$defaults` in an override
  stay literal.
- A dotlist key cannot address a list item (`items.0.x`). Use a `dict` with the whole
  list instead.
- A `$meta` or construction key introduced by an override is stripped like any other.

## Errors

Overrides of another type raise `ValueError` (`Unsupported overrides type`). A
malformed dotlist entry such as `"a"` is not an error: OmegaConf sets `a` to `None`.
