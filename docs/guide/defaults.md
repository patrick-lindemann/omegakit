# Defaults

`$defaults` gives every mapping next to it the same settings, and each mapping's own
values win. It suits lists of similar things, such as `webapp`'s scheduled jobs:

```{literalinclude} ../examples/webapp/configs/jobs.yaml
:language: yaml
:caption: configs/jobs.yaml
```

```{literalinclude} ../examples/guide/defaults/main.py
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
with `$base` and still get the defaults. When `$defaults` are nested, the inner one
wins, because it has already been applied when the outer one is.

A `$defaults` that is not a mapping raises `ConfigValidationError`. Precedence in
full is in the contracts under [Precedence](../contracts/assembly.md#precedence).
