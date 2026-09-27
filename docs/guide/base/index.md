# Base

`$base` merges shared settings underneath a node. Use it when several files share
most of their values and differ in a few, as `webapp`'s environments do:

```{literalinclude} ../../webapp/configs/base.yaml
:language: yaml
:caption: configs/base.yaml (excerpt)
:end-before: "cache:"
```

```{literalinclude} ../../webapp/configs/envs/prod.yaml
:language: yaml
:caption: configs/envs/prod.yaml
```

```{literalinclude} main.py
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

```{literalinclude} hosts.yaml
:language: yaml
:caption: hosts.yaml
```

`site.allowed_hosts` is `[c.example.com]`, and `timeout` is 30.

A `$base` may also be a list of mappings. Later entries win over earlier ones, and
the node's own keys win over all of them.

## Rules

- `$base` is a mapping or a list of mappings. Anything else raises
  `ConfigValidationError` naming the node.
- Precedence, strongest first: the node's own keys, later list items, earlier list
  items. Lists inside the merged mappings are replaced, not joined.
- Every `$base` is merged before any `$defaults` is applied. A `$base` therefore
  does not see keys that a `$defaults` adds. A `$defaults` key inside a
  referenced node is copied as written, and then applies to the new node's
  children too.

A `${…}` base is resolved while assembling, and is a copy taken when it is merged:

- It sees the referenced node with that node's own `$base` merged, and waits
  until that has happened ([Loading](../loading/index.md#rules)).
- It cannot refer to keys that an enclosing node's own `$base` brings in.
  `replica: {$base: ${db}}` in a file whose root has `$base: ~import common.yaml`,
  with `db` coming from `common.yaml`, raises.
- In a file used as another file's `$base`, the copy is taken there, before the
  other file's keys apply. Replacing `db` later does not change the copy.
- Overrides do not reach the copy: `db.pool=9` leaves `replica.pool` unchanged.
- A relative reference to a sibling in the same file, `${..db}`, works wherever
  that file ends up.
