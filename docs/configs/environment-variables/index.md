# Environment variables

A config reads environment variables through OmegaConf's `oc.env` resolver. It is
built into OmegaConf, so it works without any registration. `webapp` uses it twice:
the root file picks the environment, and production reads its secret key.

```{literalinclude} ../../webapp/configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

```{literalinclude} ../../webapp/configs/envs/prod.yaml
:language: yaml
:caption: configs/envs/prod.yaml (excerpt)
:lines: 3-6
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
webapp.db.Postgres
s3cr3t-from-the-vault
```

`APP_ENV=prod` made the root file import `envs/prod.yaml`, and the secret key came
from `SECRET_KEY`. A resolved config holds the real secret, as the second line
shows. To log a config with its secrets masked, see
[Masking secrets](../../security/secrets/index.md).

omegakit does not read `.env` files. Load them with a tool such as `python-dotenv`
before loading the config.

## Rules

- `${oc.env:NAME}` reads the variable `NAME` when the value is resolved, and
  `${oc.env:NAME,default}` falls back to `default`.
- In an `~import` path, and in the values of `$base` and `$defaults`, the variable
  is read while loading ([Loading](../loading/index.md#rules)). Everywhere else it
  is read when the value is read, validated or built.
- A variable that is not set and has no default fails like any interpolation
  ([Interpolation](../interpolation/index.md#rules)).
