# Base

`$base` merges one mapping, or a list of mappings, underneath the node it appears in.
It is how a node extends shared settings.

## Example

```{literalinclude} ../examples/base/common.yaml
:language: yaml
:caption: common.yaml
```

```{literalinclude} ../examples/base/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/base/main.py
:language: python
:caption: main.py
```

## Precedence

From strongest to weakest:

1. Overrides.
2. The node's own keys.
3. Later items of a `$base` list.
4. Earlier items of a `$base` list.

## Rules

- The value is usually an `~import` or an interpolation such as `${_fast}`. An
  interpolation sees the referenced node as assembled so far.
- Bases are merged children before parents, so a nested `$base` is merged before the
  node that contains it.
- The `$base` key itself is removed after merging.
- Helper nodes such as `_fast` stay in the config. omegakit gives no meaning to a
  leading underscore.

**Known limitation:** a `$base: ${other}` that points at a node later in the file,
which has its own `$base`, sees that node unmerged. Reference earlier nodes, or
nodes without their own `$base`. See the [contracts](../contracts.md), section 3.

## Errors

A `$base` that is not a mapping or a list of mappings raises `ValueError`.
