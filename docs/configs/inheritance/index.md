# Inheritance

`$base` merges shared settings underneath a node. Use it when several files share
most of their values and differ in a few, as `curvefit`'s experiments do:

```{literalinclude} ../../curvefit/configs/experiments/linear-sgd.yaml
:language: yaml
:caption: configs/experiments/linear-sgd.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: sweep.yaml
```

```text
linear-sgd 0 200
200 1234
```

`name` comes from the experiment file, which wins over the `name: ???` of the base.
`seed` and the trainer come from `base.yaml`. Overrides win over both.

The base can also be a node of the same file, referenced with `${…}`. The test
split takes the settings of the training split, with a seed of its own:

```{literalinclude} ../../curvefit/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:start-at: "  train:"
:end-before: "trainer:"
```

The reference is relative (`..` is the parent of `test`), so it finds `train`
wherever `base.yaml` ends up, even as the base of an experiment file.

Lists are replaced, not joined:

```{literalinclude} sweep.yaml
:language: yaml
:caption: sweep.yaml
```

```{literalinclude} main.py
:language: python
:start-at: sweep.yaml
```

```text
[0] [3, 5]
```

A `$base` may also be a list of mappings. Later entries win over earlier ones, and
the node's own keys win over all of them.

## Rules

- `$base` is a mapping or a list of mappings. Anything else raises
  `ConfigLoadError` naming the node.
- Precedence, strongest first: the node's own keys, later list items, earlier list
  items. Lists inside the merged mappings are replaced, not joined.
- Every `$base` is merged before any `$defaults` is applied. A `$base` therefore
  does not see keys that a `$defaults` adds. A `$defaults` key inside a
  referenced node is copied as written, and then applies to the new node's
  children too.

A `${…}` base is resolved while assembling, and is a copy taken when it is merged:

- It sees the referenced node with that node's own `$base` merged, and waits
  until that has happened ([Loading](../loading/index.md#rules)).
- It cannot refer to keys that an enclosing node's own `$base` brings in.
  `test: {$base: ${train}}` in a file whose root has `$base: ~import base.yaml`,
  with `train` coming from `base.yaml`, raises.
- In a file used as another file's `$base`, the copy is taken there, before the
  other file's keys apply. Replacing `data.train` there does not change the copy.
- Overrides do not reach the copy: `data.train.n=100` leaves `data.test.n`
  unchanged.
- A relative reference to a sibling in the same file, `${..train}`, works wherever
  that file ends up.
