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
nested `dict` passed to `apply_overrides` does the same for the config already in
memory: the optimizer kept its `momentum` and changed only its learning rate. The
function returns a copy by default, as the parameter-sweep
[recipe](../../recipes/parameter-sweeps/index.md) uses to start every run from the
same config. On the command line, `omegakit check` and `omegakit show` take the same
strings as `--overrides KEY=VALUE ...`.

## Rules

- `load_config` takes overrides as a list of `key=value` strings, a `dict` or a
  `DictConfig`. `instantiate` and `prepare` take none; change a config in memory
  with `apply_overrides(config, overrides)`.
- `apply_overrides` returns a copy. Pass `copy=False` to change the config itself.
- The strings apply one at a time, in order, so a later one wins over an earlier
  one. Each value is parsed as YAML: `epochs=50` is an integer, `seeds=[0, 1]` a
  list. A dotted key adds the mappings it names, as `a.b=1` adds `a`.
- A mapping merges into the config: its keys replace those of the node they name,
  and the node's other keys stay. To replace a whole node, assign it in code, such
  as `config.optimizer = {...}`.
- Overrides apply after the includes, `$base` and `$each`, and win over every value
  of the files ([Precedence](../loading/index.md#rules)). A `$base` or `$each` in an
  override stays a plain key, and an `~include` in a mapping stays text. When called
  through `load_config`, `$meta` is removed from overrides too unless
  `keep_meta=True`; `apply_overrides` itself leaves `$meta` in place.
- These raise `ConfigOverrideError`:
  - an item of the list that is not a string, as in ``An override in a list must be
    a `key=value` string, not `1`.``;
  - an item without `=` or without a key, as in `` `seed` is not an override:
    write it as `key=value`. ``;
  - a key with `[`, such as `layers[0]=1`: give the whole list instead;
  - a value that cannot be parsed, as in ``Cannot parse `seeds=[0`: …``;
  - a value that is an `~include`, which arrives after the includes are resolved;
  - overrides of another type, a `ListConfig` included, as in ``Cannot override a
    `DictConfig` with a `ListConfig`.``;
  - an override that cannot be applied, named in the message, as in ``Cannot apply
    `seeds.first=0`: Cannot merge incompatible container types`` where `seeds` is
    a list.
