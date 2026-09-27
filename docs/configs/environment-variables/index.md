# Environment variables

A config reads environment variables through OmegaConf's `oc.env` resolver. It is
built into OmegaConf, so it works without any registration. `curvefit`'s tracker
can post its metrics to a server, and the URL holds a token that must stay out of
git:

```{literalinclude} tracked.yaml
:language: yaml
:caption: tracked.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
Cannot resolve `tracker.url`: KeyError raised while resolving interpolation: "Environment variable 'TRACKER_TOKEN' not found"
https://tracker.example.com/api/runs?token=tok-5f3a9c1e7b2d4f60
```

The variable is read when the value is resolved, not while loading. So the config
loads without it, and fails when it is validated, built or read. The resolved URL
holds the real token, as the second line shows. To log a config with its secrets
masked, see [Masking secrets](../../security/masking-secrets/index.md).

omegakit does not read `.env` files. Load them with a tool such as `python-dotenv`
before loading the config.

## Rules

- `${oc.env:NAME}` reads the variable `NAME` when the value is resolved, and
  `${oc.env:NAME,default}` falls back to `default`.
- In an `~import` path, and in the values of `$base` and `$defaults`, the variable
  is read while loading ([Loading](../loading/index.md#rules)). Everywhere else it
  is read when the value is read, validated or built.
- A variable that is not set and has no default fails like any interpolation
  ([Interpolation](../interpolation/index.md#rules)), also with
  `allow_missing=True`.
