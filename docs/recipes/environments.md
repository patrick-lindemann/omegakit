# One config per environment

Development and production share most settings and differ in a few: the database,
the number of workers, where the secret comes from. Keep the shared settings in one
file, give each environment a small file that uses it as its `$base`, and let the
root file pick one with an environment variable.

```{literalinclude} ../examples/webapp/configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

```{literalinclude} ../examples/webapp/configs/envs/dev.yaml
:language: yaml
:caption: configs/envs/dev.yaml
```

```{literalinclude} ../examples/webapp/configs/envs/prod.yaml
:language: yaml
:caption: configs/envs/prod.yaml
```

`configs/base.yaml` holds everything else. Building the app in each environment:

```{literalinclude} ../examples/recipes/environments/main.py
:language: python
:caption: main.py
```

```text
dev SQLite 1
prod Postgres 8
```

The same code builds a SQLite app with one worker in development and a Postgres app
with eight in production, and a new environment is one more small file.

## Values every environment must fill

The secret key has no sensible shared value, so `base.yaml` leaves it open with
`secret_key: ???`. Development gives a fixed key, and production reads its key from
the `SECRET_KEY` environment variable. If an environment forgets it, validating or
building fails and names `server.secret_key`.

`base.yaml` on its own is incomplete on purpose, but it can still be checked, for
every value it does give:

```sh
omegakit check configs/base.yaml --schema webapp.App --allow-missing
```

The last line of `main.py` does the same from Python. See [Base](../guide/base.md)
and [Interpolation and missing values](../guide/interpolation-and-missing.md) for
the features used here.
