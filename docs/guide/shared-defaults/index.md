# Shared defaults

`$defaults` gives every mapping next to it the same settings, and each mapping's own
values win. It suits groups of similar things, such as the splits of a dataset:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
train 256 0.1 0
validation 64 0.1 1
test 256 0.1 1234
```

Every split got `n` and `noise` from `$defaults`, and each keeps its own `seed`. The
validation split also keeps its own `n`. Only mappings receive the defaults:
scalars, lists and `$` keys next to `$defaults` stay as they are, and nested
mappings are reached only through a split's own keys.

## Rules

- `$defaults` is a mapping. Anything else raises `ConfigLoadError` naming the
  node.
- It reaches only the mapping-valued siblings in its own mapping. Scalars, lists
  and `$` keys are untouched, and grandchildren only through the sibling's own
  keys.
- It is weaker than the sibling's own keys, including the keys the sibling's own
  `$base` brought in, because bases are merged first. When `$defaults` are nested,
  the inner one wins, because it is applied first.
- It is applied after every `$base` in the config, so a `$defaults` that arrives
  through a `$base` or an `~import` works. A `$defaults` copied through a `${…}`
  base applies at the new place too ([Inheritance](../inheritance/index.md#rules)).
- A `${…}` value of `$defaults` sees the referenced node with that node's own
  `$base` merged and `$defaults` applied, and waits until that has happened
  ([Loading](../loading/index.md#rules)).
