# Defaults

`$defaults` gives every dict-valued sibling in its mapping the same defaults. Each
item's own values win. It suits manifests, where many entries share most settings.

## Example

```{literalinclude} ../examples/defaults/datasets.yaml
:language: yaml
:caption: datasets.yaml
```

```{literalinclude} ../examples/defaults/main.py
:language: python
:caption: main.py
```

## Rules

- Only dict-valued siblings receive defaults. Scalars, lists and `$` keys are left
  alone, and grandchildren are reached only through the sibling's own keys.
- `$defaults` is applied after every `$base` is merged, so an item's `$base` and the
  defaults combine. A `$defaults` that arrives through a `$base` or an `~import`
  works too.
- Nested `$defaults` are applied children before parents, so an inner `$defaults`
  wins over an outer one.
- `$defaults` may contain `$class`, which makes every item instantiable; see the
  [manifest recipe](../cookbook.md#dataset-manifests).

## Errors

A `$defaults` that is not a mapping raises `ValueError`.
