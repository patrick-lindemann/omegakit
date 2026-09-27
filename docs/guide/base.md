# Base

`$base` merges shared settings underneath a node. Use it when several files share
most of their values and differ in a few, as `webapp`'s environments do:

```{literalinclude} ../examples/webapp/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:end-before: "cache:"
```

```{literalinclude} ../examples/webapp/configs/envs/prod.yaml
:language: yaml
:caption: configs/envs/prod.yaml
```

```{literalinclude} ../examples/guide/base/main.py
:language: python
:caption: main.py
```

```text
{'host': '0.0.0.0', 'port': 8000, 'workers': 8, 'secret_key': '${oc.env:SECRET_KEY}'}
{'url': 'postgres://db-replica.internal/webapp', 'pool_size': 20}
```

`workers` is 8 because `prod.yaml`'s own keys win over the base, and `port` comes
from `base.yaml`. Overrides win over both. The database is swapped by giving the
whole node, `$class` and `url` included, so nothing of the SQLite settings is left
behind.

The base can also be a node of the same file, referenced with `${…}`. The replica
above is a second Postgres with its own URL and the primary's pool size. The
reference is relative (`..` is the parent of `replica`), so it finds `database`
wherever `prod.yaml` ends up, even under the root file's own `$base`.

Lists are replaced, not joined:

```{literalinclude} ../examples/guide/base/hosts.yaml
:language: yaml
:caption: hosts.yaml
```

`site.allowed_hosts` is `[c.example.com]`, and `timeout` is 30.

A `$base` may also be a list of mappings: later entries win over earlier ones, and
the node's own keys win over all of them. A `$base` that is not a mapping or a list
of mappings raises `ConfigValidationError`. The contracts cover merge order and
precedence in [Precedence](../contracts.md#precedence), and what a `${…}` base can
see in [Resolution timing](../contracts.md#resolution-timing).
