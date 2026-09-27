# Swapping an implementation

The application needs a database; production uses Postgres, development and tests
use SQLite. Type the field with the base class, name the implementation with
`$class` in the config, and swap the whole node per environment or per test.

```{literalinclude} ../../webapp/webapp/db.py
:language: python
:caption: webapp/db.py
```

`AppConfig` declares `database: Database`, so any subclass is accepted.
`base.yaml` names `webapp.db.SQLite`, and `envs/prod.yaml` replaces the whole node
with a Postgres one. A test swaps it once more, with a dict override:

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
SQLite sqlite://
`database` expects Database, but the config gives `$class: webapp.cache.RedisCache`.
```

The code that uses `app.database` never names a class, and a class that is not a
`Database` is rejected before anything is built. Override `$class` alone only when
the new class takes the same settings; otherwise swap the whole node, so that no
setting of the old class is left behind. See
[Instantiation](../../objects/instantiation/index.md) and
[Schemas](../../objects/schemas/index.md).
