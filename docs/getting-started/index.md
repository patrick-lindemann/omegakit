# Getting started

This page builds the config of `webapp`, a small web service with a server and a
database, in six steps. The first four use plain classes with nothing
omegakit-specific in them.

```sh
pip install omegakit
```

## 1. Load a file and read values

```{literalinclude} step1.yaml
:language: yaml
:caption: step1.yaml
```

```python
from omegakit import load_config

config = load_config("step1.yaml")
config.server.port  # 8000
```

`load_config` returns an OmegaConf `DictConfig`, so everything OmegaConf offers
works on it.

## 2. Build an object from it

The server is a plain class:

```{literalinclude} plain.py
:language: python
:caption: plain.py
:pyobject: Server
```

`$class` on the node names the class to build, and `instantiate` calls it with the
node's other keys:

```{literalinclude} step2.yaml
:language: yaml
:caption: step2.yaml
```

```python
from omegakit import instantiate
from plain import Server

server = instantiate(config.server, Server)
```

`$class` decides what is built. The second argument only gives the result its type
for your editor.

## 3. One file per environment

Development and production share most settings. They go into `base.yaml`, and each
environment file keeps only what differs. `~import` pastes another file in, and
`$base` makes it the layer underneath the node, so the node's own keys win:

```{literalinclude} configs/base.yaml
:language: yaml
:caption: configs/base.yaml
```

```{literalinclude} configs/envs/prod.yaml
:language: yaml
:caption: configs/envs/prod.yaml
```

The root file picks the environment from the `APP_ENV` variable, with `dev` as the
default:

```{literalinclude} configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

Production swaps the whole database node, so `instantiate(config.database,
Database)` gives a `SQLite` in development and a `Postgres` in production. This is
why configs name classes: the code asks for a database, and the config decides
which one.

## 4. Values from outside

`secret_key: ???` in the base is a slot that every environment must fill. Production
fills it from the environment with OmegaConf's `oc.env` resolver, and anything can
be overridden when loading:

```python
config = load_config("configs/app.yaml", overrides=["server.port=9000"])
```

A slot that is still `???` fails when the config is validated or built, naming the
key. See [Overrides and environment variables](../guide/overrides/index.md).

## 5. Add a schema

So far a typo such as `worker: 4` is a `TypeError` from the constructor, and
`port: abc` is accepted without complaint. A dataclass schema catches both. The
class subclasses `Configurable` with its schema:

```{literalinclude} ../webapp/webapp/server.py
:language: python
:caption: webapp/server.py
```

`validate(config, schema=App)` now raises a `ConfigValidationError` that names the
key, one mistake at a time:

```text
Unknown field(s) 'worker' in `server` (ServerConfig). Expected one of: host, port, workers, secret_key.
Invalid config in `server.port` (ServerConfig): Value 'abc' of type 'str' could not be converted to Integer
```

`instantiate` runs the same check before it builds anything. See
[Typed configs](../guide/typed-configs/index.md) and [Validation](../guide/validation/index.md).

## 6. Use it in your service

The complete `webapp` has a root class, `App`, whose schema holds the server, the
database, an optional cache and scheduled jobs. The entrypoint loads the config,
logs it with its secrets masked, and builds the app:

```{literalinclude} ../webapp/main.py
:language: python
:caption: main.py
```

```sh
APP_ENV=prod SECRET_KEY=change-me-in-production python main.py server.port=9000
```

```text
...
server:
  $class: webapp.server.Server
  host: 0.0.0.0
  port: 9000
  workers: 8
  secret_key: '***'
...
serving on 0.0.0.0:9000 with 8 workers
database: Postgres postgres://db.internal/webapp
replica: Postgres postgres://db-replica.internal/webapp
cache: RedisCache, 600 s
job digest, every 7d: sent 'What happened this week'
job cleanup, every 1h: purged expired sessions
```

To check the configs before every commit, run `omegakit check` as a
[pre-commit](https://pre-commit.com) hook. It validates each file against the
schema of `App`. Checking runs code from the files, so run it only on changes from
people you trust, and limit the modules a file can name with `--allow-module`
([Security](../security/index.md)):

```sh
omegakit check configs/app.yaml --schema webapp.App --allow-module webapp
```

Tests load the same config with an override that puts an in-memory database under
`database`:

```{literalinclude} ../webapp/tests/conftest.py
:language: python
:caption: tests/conftest.py
```

Your editor can complete and check these files too: see
[Editor schemas](../guide/editor-schemas/index.md). From here, the guide covers each feature,
starting with [Loading](../guide/loading/index.md).
