# Defaults

`$each` gives every mapping beside it the same settings, and each mapping's own
values win. It suits groups of similar things, such as the splits of a dataset:

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

config.data.train: {'n': 256, 'noise': 0.1, 'seed': 0}
config.data.validation: {'n': 64, 'noise': 0.1, 'seed': 1}
config.data.test: {'n': 256, 'noise': 0.1, 'seed': 1234}
```

Every split got `n` and `noise` from `$each`, and each keeps its own `seed`. The
validation split also keeps its own `n`.

## Rules

- `$each` is a mapping, often a `${…}`. Anything else raises `ConfigMergeError`, as
  in `` `$each` must be a mapping, not `[1]`. (at `data`) ``.
- It is merged under every key of its own mapping that holds a mapping and does not
  start with `$`. Values, lists, `null`, `???` and `${…}` are left alone, and so are
  grandchildren, except through the keys of `$each` itself.
- It is weaker than the mapping's own keys, including the keys that the mapping's
  own `$base` brought in, because bases are merged first. When `$each` are nested,
  the inner one wins, because it is merged first.
- It is merged after every `$base` in the config, so an `$each` that arrives
  through a `$base` or an `~include` works. An `$each` copied through a `${…}` base
  applies at the new place too ([Inheritance](../inheritance/index.md#rules)).
- A `${…}` value of `$each` is resolved while loading. It waits, as a `$base` does,
  until no `$each` is left in what it reads, so it sees the referenced mapping with
  its `$base` and `$each` merged ([Inheritance](../inheritance/index.md#rules)). One
  that cannot be resolved raises ``ConfigMergeError: Cannot resolve `$each`: …``.
