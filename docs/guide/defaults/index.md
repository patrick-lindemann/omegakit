# Defaults

`$defaults` gives every mapping next to it the same settings, and each mapping's own
values win. It suits lists of similar things, such as `webapp`'s scheduled jobs:

```{literalinclude} ../../webapp/configs/jobs.yaml
:language: yaml
:caption: configs/jobs.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
digest webapp.jobs.Job 3 7d
cleanup webapp.jobs.Job 1 1h
```

Both jobs got `$class` and `retries` from `$defaults`, so both are built as a `Job`,
and `cleanup` keeps its own `retries: 1`. Only mappings receive the defaults:
scalars, lists and `$` keys next to `$defaults` stay as they are, and nested
mappings are reached only through a job's own keys.

Defaults are applied after every `$base` is merged, so a job can extend another job
with `$base` and still get the defaults.

## Rules

- `$defaults` is a mapping. Anything else raises `ConfigValidationError` naming
  the node.
- It reaches only the mapping-valued siblings in its own mapping. Scalars, lists
  and `$` keys are untouched, and grandchildren only through the sibling's own
  keys.
- It is weaker than the sibling's own keys, including the keys the sibling's own
  `$base` brought in, because bases are merged first. When `$defaults` are nested,
  the inner one wins, because it is applied first.
- It is applied after every `$base` in the config, so a `$defaults` that arrives
  through a `$base` or an `~import` works. A `$defaults` copied through a `${…}`
  base applies at the new place too ([Base](../base/index.md#rules)).
- A `${…}` value of `$defaults` sees the referenced node with that node's own
  `$base` merged and `$defaults` applied, and waits until that has happened
  ([Loading](../loading/index.md#rules)).
