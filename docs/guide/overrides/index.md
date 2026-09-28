# Overrides

Overrides change values after a config is assembled, and win over everything in the
files:

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

config.model.hidden: 64
config.epochs: 50
config.optimizer.lr: 0.001
config.optimizer.momentum: 0.9
```

A list of `key=value` strings is what a command line gives you, so a script can pass
its arguments straight to `load_config`. `model.hidden=64` became the integer 64. A
nested `dict` does the same from code: the optimizer kept its `momentum` and changed
only its learning rate. `instantiate` and `prepare` take `overrides=` too.

## Rules

- `overrides` is a `DictConfig`, a `dict`, or a list of `key=value` strings. Any
  other type, including a `ListConfig`, raises `TypeError`.
- Each value in a list is parsed as YAML: `epochs=50` is an integer,
  `seeds=[0, 1]` a list. A string without `=`, such as `a`, sets `a` to `null`.
- An override that does not parse, has a value OmegaConf does not support, or is
  rejected by a struct config raises `ConfigLoadError` from `load_config`,
  `instantiate` and `prepare`, naming the override or its key.
- Overrides are merged after assembly. An `~import`, `$base` or `$defaults` in an
  override stays literal. `$meta`, and with `keep_targets=False` also `$class`,
  `$ref` and `$partial`, are stripped from overrides too.
- A mapping merges into the node it names: its keys replace those of the node, and
  the node's other keys stay. To replace a whole node, assign it in code, such as
  `config.optimizer = {...}`.
- Overrides win over every value from the files
  ([Precedence](../loading/index.md#rules)). `instantiate` and `prepare` merge
  theirs into a copy of the node and leave the config passed in unchanged.
