# Metadata

`$meta` holds notes for people and tools, such as a title, a description, a version
and an author. Any mapping can have one, and it is never part of the values:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

config: {'seed': 0, 'model': {'hidden': 256}}
config.$meta.title: Wide MLP
config.$meta.version: 2
description: The baseline MLP with eight times as many hidden units.
description: Wider than the baseline's 32 units.
```

`load_config(..., keep_meta=True)` kept the metadata, and `remove_meta` made the
copy printed first without changing that config. `walk` visited every node, parents
first, and the script kept the mappings that hold `$meta`. So it found the
description of the model node too, as a script that lists experiments with their
titles would.

## Rules

- `remove_meta(config)` removes `$meta` from a config already in memory and returns
  a copy. Pass `copy=False` to transform the config itself.
- `$meta` is a key of a mapping, and its value can be anything. omegakit does not
  check what it holds.
- `load_config` removes every `$meta`, unless `keep_meta=True`
  ([Loading](../loading/index.md#rules)).
- `validate` ignores `$meta` in every mapping. It may stand next to `$target` and
  `$symbol`, and building never passes it to a constructor or to `from_config`
  ([Instantiation](../../objects/instantiation/index.md)).
- `walk(node, order="pre-order")` yields `node` and every node below it: mappings,
  lists and single values. In `"pre-order"` a node comes before its children, in
  `"post-order"` after them. It does not resolve interpolations.
