# Shared defaults

`$defaults` gives every mapping next to it the same settings, and each mapping's own
values win. It suits groups of similar things, such as `curvefit`'s data splits:

```{literalinclude} ../../curvefit/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:start-at: "data:"
:end-before: "trainer:"
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
train curvefit.data.Synthetic 0.1 200 0
validation curvefit.data.Synthetic 0.1 50 1
test curvefit.data.Synthetic 0.1 200 1234
```

All three splits got `$class`, `function` and `noise` from `$defaults`, here
imported from the sine preset ([Imports](../imports/index.md)), and each keeps its
own `n` and `seed`. Only mappings receive the defaults: scalars, lists and `$` keys
next to `$defaults` stay as they are, and nested mappings are reached only through
a split's own keys.

Defaults are applied after every `$base` is merged, so the test split can extend
the training split with `$base` and still get the defaults.

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
