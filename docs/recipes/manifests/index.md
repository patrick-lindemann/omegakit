# A manifest of similar things

An application often has a list of things that share most settings: scheduled jobs,
queues, feeds. Put them in one mapping, give it the shared settings with
`$defaults`, let one entry extend another with `$base`, and record who owns each
entry with `$meta`.

```{literalinclude} jobs.yaml
:language: yaml
:caption: jobs.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
digest: every 7d, retries 3, owner growth
  sent 'What happened this week'
monthly_digest: every 30d, retries 3, owner growth
  sent 'What happened this month'
cleanup: every 1h, retries 1, owner platform
  purged expired sessions
```

Every entry is a `Job`, because `$defaults` gives each one `$class`. The monthly
digest copies the weekly one and changes its subject and schedule, and `cleanup`
keeps its own `retries`. `keep_meta=True` keeps the owners for the report; a
constructor never sees them. See [Defaults](../../configs/defaults/index.md),
[Base](../../configs/base/index.md) and [Building objects](../../objects/building-objects/index.md).
