# Typed configs

A class that subclasses `Configurable[TConfig]`, with a dataclass `TConfig`, has a
schema. Its config is checked against the dataclass before anything is built, and
the class receives the checked values, with the right types for your editor.
Classes without a schema keep working as plain `$class` targets.

`webapp`'s server is the simplest case:

```{literalinclude} ../examples/webapp/webapp/server.py
:language: python
:caption: webapp/server.py
```

```{literalinclude} ../examples/guide/typed-configs/main.py
:language: python
:caption: main.py
```

```text
9000 1
RedisCache 600
MemoryCache
EmailNotifier
```

`port: "9000"` became the integer 9000, and `workers` took its default. A key the
schema does not have, or a value it cannot convert, raises `ConfigValidationError`
naming the key. `check_schema(Server)` checks that the schema fits the constructor:
every required parameter has a field, and every field is a parameter of a matching
type. It runs by itself before the first build; call it in a test to catch a
mismatch without a config.

## Field kinds

The application's schema shows the three kinds of field:

```{literalinclude} ../examples/webapp/webapp/__init__.py
:language: python
:caption: webapp/__init__.py (excerpt)
:pyobject: AppConfig
```

- **Values:** `int`, `float`, `bool`, `str`, `Path`, enums, `Literal`, dataclasses
  of these, and `list`, `dict`, `tuple` or unions of these, such as `log_dir`.
  They are converted and checked like `port` above.
- **Objects:** any other class, such as `server: Server` or `jobs: dict[str, Job]`.
  The config holds a `$class` node of that class or a subclass, or a `$ref` to an
  instance, and the typed config holds the built object. `database: Database`
  accepts both `Postgres` and `SQLite`.
- **`Any`:** the value is not checked, but `$class` nodes and reserved keys inside
  it are. `JobConfig.handler` is `Any`, because it holds a function.

## A custom `from_config`

`from_config` receives the typed config, with object fields already built, and
calls the constructor. The default passes every field. Override it when the config
and the constructor differ, as the cache does with its `ttl`:

```{literalinclude} ../examples/webapp/webapp/cache.py
:language: python
:caption: webapp/cache.py
```

Keep `**kwargs` in the signature: arguments given to a partial from `prepare` arrive
there. `from_config` is looked up by name, so any class with that classmethod
works the same, `Configurable` or not.

Children that code chooses, rather than the user, are created with `make_node`.
`App.from_config` builds an in-memory cache when the config has none, which is why
`cache=null` gave a `MemoryCache` above:

```{literalinclude} ../examples/webapp/webapp/__init__.py
:language: python
:pyobject: App.from_config
```

## Factories

A `from_config` that returns a subclass annotates the base class as its return
type, since `Self` would claim the class it was called on:

```{literalinclude} ../examples/guide/typed-configs/notify.py
:language: python
:caption: notify.py
```

A `TypedDict` `TConfig` gives `from_config` static types only: it receives a plain
`dict`, and the field values are not checked, though `$class` nodes inside are. The supported dataclass features, and the error for
each unsupported one, are in the contracts under
[Typed configs](../contracts.md#typed-configs).
