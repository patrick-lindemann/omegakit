# Inheritance

`$base` merges shared settings underneath a node. Use it when several files share
most of their values and differ in a few. A base file holds the common settings:

```{literalinclude} base.yaml
:language: yaml
:caption: base.yaml
```

An experiment names it as its `$base` and writes only what differs. The base
arrives through an [import](../imports/index.md), which is how a base file is
usually named:

```{literalinclude} wide.yaml
:language: yaml
:caption: wide.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: sweep.yaml
```

```{code-block} text
:caption: Output

config.model.hidden: 256
config.model.layers: 2
config.optimizer.lr: 0.01
config.epochs: 200
```

The merge is deep: `wide.yaml` changed the model's `hidden` and kept its `layers`.
Its own keys win over the base, and everything it does not mention comes from the
base.

The base can also be a node of the same file, named by a reference:

```{literalinclude} sweep.yaml
:language: yaml
:caption: sweep.yaml
```

```{literalinclude} main.py
:language: python
:start-at: sweep.yaml
```

```{code-block} text
:caption: Output

config.quick.seeds: [0]
config.quick.hidden: [32, 256]
```

`quick` took `hidden` from `full` and replaced its `seeds`: lists are replaced, not
joined. `..` is the parent of `quick`, so the reference finds `full` wherever the
file ends up. A `$base` may also be a list of mappings (see Rules).

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
