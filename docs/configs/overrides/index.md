# Overrides

Overrides change values after a config is assembled, and win over everything in the
files.

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
5 50
0.01 curvefit.optim.Adam
```

A list of `key=value` strings is what a command line gives you, so `curvefit`'s
`main.py` passes the arguments after the experiment file straight to `load_config`.
Values are read as YAML: `model.degree=5` is an integer. A nested `dict` does the
same from code. It merges into the node it names, so the optimizer above kept its
`$class` and changed only its learning rate.

`instantiate` and `prepare` take `overrides=` too. They merge them into a copy of the
node they build and leave the config you passed unchanged.

Overrides arrive after the files are assembled, so an `~import`, `$base` or
`$defaults` inside an override stays literal. They carry the same trust as the
files, so never build them from untrusted input
([Trust model](../../security/trust-model/index.md)).

## Rules

- `overrides` is a `DictConfig`, a `dict`, or a list of `key=value` strings. Any
  other type, including a `ListConfig`, raises `TypeError`.
- Each value in a list is parsed as YAML: `trainer.epochs=50` is an integer,
  `seeds=[0, 1]` a list. A string without `=`, such as `a`, sets `a` to `null`.
- An override that does not parse, has a value OmegaConf does not support, or is
  rejected by a struct config raises `ConfigValidationError` from `load_config`,
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
