# Inheritance

`$base` merges shared settings under a node. Use it when several files share most
of their values and differ in a few. A base file holds the common settings:

```{literalinclude} base.yaml
:language: yaml
:caption: base.yaml
```

An experiment names it as its `$base` and writes only what differs. The base
arrives through an [include](../includes/index.md), which is how a base file is
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

The base can also be a node of the same file, named by an interpolation:

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
joined. `..` is the parent of `quick`, so the interpolation finds `full` wherever
the file ends up. A `$base` may also be a list of mappings (see Rules).

## Rules

- `$base` is a mapping or a list of mappings, usually an `~include` or a `${…}`.
  Anything else, `null` and `???` included, raises `ConfigMergeError`, as in
  `` `$base` must be a mapping or a list of mappings, not `5`. (at `model`) ``.
- The bases are merged under the node, as by `OmegaConf.merge(*bases, node)`.
  Precedence, strongest first: the node's own keys, later list items, earlier list
  items. Lists inside the merged mappings are replaced, not joined. An own `???`
  does not replace a value of the base: the base's value stays.
- Every `$base` is merged before any `$each` is merged. A `$base` therefore does not
  see keys that an `$each` adds, and an `$each` inside a referenced node is copied
  as written and applies at the new place too.

A `${…}` base is resolved while loading, and is a copy taken when it is merged:

- A node's `$base` is merged once nothing that the merge reads still holds a
  `$base`: the node, the referenced mapping, and the nodes that enclose that
  mapping but not the node. The node so sees the referenced mapping with that
  mapping's own `$base` merged.
- It does not wait for the `$base` of an enclosing node. `${..train}` sees `train`
  without the keys that a `$base` of its parent or of the root brings in. If
  `train` exists only through such a base, loading raises ``Cannot resolve `$base`:
  Interpolation key '..train' not found (resolved to 'data.train') (at
  `data.test`)``.
- In a file used as another file's `$base`, the copy is taken there, before the
  other file's keys apply. Replacing `data.train` there does not change the copy.
- Overrides do not reach the copy: `data.train.n=100` leaves `data.test.n`
  unchanged.
- A `${…}` that cannot be resolved raises ``ConfigMergeError: Cannot resolve
  `$base`: …``, and nodes whose `$base` refer to each other raise ``The `$base` of
  these nodes wait for each other: `a` -> `b` -> `a`.``
