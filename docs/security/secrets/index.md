# Secrets

A secret, such as the token of a tracking server, must stay out of git, out of
saved configs and out of logs. Read it from the environment with `${secret:NAME}`,
and save and log configs unresolved:

```{literalinclude} tracked.yaml
:language: yaml
:caption: tracked.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

OmegaConf.to_yaml(config):
tracking:
  project: sine
  url: https://tracker.example.com/api/runs?token=${secret:TRACKER_TOKEN}
config.tracking.url: https://tracker.example.com/api/runs?token=tok-5f3a9c1e7b2d4f60
```

The config from `load_config` is not resolved, so it shows where the token comes
from, not the token. Save and log that config. Your code still reads
the real URL, for example to pass it to a tracking client. `omegakit show
--resolve` masks the token:

```sh
omegakit show tracked.yaml --node tracking --resolve
```

```{code-block} text
:caption: Output

project: sine
url: https://tracker.example.com/api/runs?token=***
```

Only values from `${secret:...}` are masked (see Rules). To catch a secret committed
by mistake, run a scanner such as
[detect-secrets](https://github.com/Yelp/detect-secrets) or
[gitleaks](https://github.com/gitleaks/gitleaks) as a pre-commit hook. Keep secrets
out of arguments that your code saves, such as hyperparameters in checkpoints.

## Rules

- `register_secret_resolver(*, replace=False)` from `omegakit.resolvers.secrets`
  registers `${secret:NAME}`. Registration is global to OmegaConf, and a name that
  exists raises `ValueError` unless `replace=True`
  ([Overview](../../resolvers/overview/index.md#rules)). The `omegakit` command
  registers it itself.
- `${secret:NAME}` gives the value of the environment variable `NAME`, read when
  the value is resolved, as `${oc.env:NAME}` is
  ([Environment variables](../../guide/environment-variables/index.md#rules)). It
  has no default. A variable that is not set fails like any resolver error, also
  with `allow_missing=True`.
- A config from `load_config` holds `${secret:NAME}` as written.
  `OmegaConf.save` and `OmegaConf.to_yaml` write it that way, unless they resolve.
- `omegakit show --resolve` loads the config with the real values, then resolves
  `${secret:NAME}` to `***` once it has checked that `NAME` is set. Every printed
  value built from a secret holds `***` in its place, also one built by another
  resolver, such as `${oc.decode:${secret:NAME}}`. The secret's value is never
  read into the output. `--show-secrets` prints the real values. Without
  `--resolve`, nothing is resolved.
- Nothing else is masked. Error messages can contain values
  ([Trust model](../trust-model/index.md)).
