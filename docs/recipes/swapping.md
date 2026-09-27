# Swapping an implementation

The application needs a database; production uses Postgres, development and tests
use SQLite. Type the field with the base class, name the implementation with
`$class` in the config, and swap the whole node per environment or per test.

```{literalinclude} ../examples/webapp/webapp/db.py
:language: python
:caption: webapp/db.py
```

`AppConfig` declares `database: Database`, so any subclass is accepted.
`base.yaml` names `webapp.db.SQLite`, and `envs/prod.yaml` replaces the node with a
Postgres one, `$class` and `url` together, so no SQLite setting is left behind. A
test swaps it once more, with a dict override:

```{literalinclude} ../examples/recipes/swapping/main.py
:language: python
:caption: main.py
```

```text
SQLite sqlite://
`database` expects Database, but the config gives `$class: webapp.cache.RedisCache`.
```

The code that uses `app.database` never names a class, and a class that is not a
`Database` is rejected before anything is built. Override `$class` alone only when
the new class takes the same settings; otherwise swap the node, as above. See
[Building objects](../guide/building-objects.md) and
[Typed configs](../guide/typed-configs.md).
