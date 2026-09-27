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

```text
$class: curvefit.tracking.Tracker
run_dir: ${run_dir}
url: https://tracker.example.com/api/runs?token=${secret:TRACKER_TOKEN}
True
```

The config from `load_config` is not resolved, so it shows where the token comes
from, not the token. Save and log that config, as
[Reproducible runs](../../reproducible-runs/index.md) does. The tracker still
receives the real URL. `omegakit show --resolve` prints each value that
`${secret:...}` gave as `***`, also inside a longer string:

```text
$ omegakit show tracked.yaml --node tracker --resolve
$class: curvefit.tracking.Tracker
run_dir: runs/poly3-adam/seed0
url: https://tracker.example.com/api/runs?token=***
```

omegakit does not guess which other values are secret. A secret written into a
file, read with `oc.env`, or held by a built object prints as it is. To catch a
secret committed by mistake, run a scanner such as
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
  ([Environment variables](../../configs/environment-variables/index.md#rules)). It
  has no default. A variable that is not set fails like any resolver error, also
  with `allow_missing=True`.
- A config from `load_config` holds `${secret:NAME}` as written.
  `OmegaConf.save` and `OmegaConf.to_yaml` write it that way, unless they resolve.
- `omegakit show --resolve` first resolves every value in the config that reads
  `${secret:...}`, also outside `--node`. It then replaces each value that
  `${secret:...}` gave in the process with `***`, wherever it appears in a printed
  string. Keys and values that are not strings are never rewritten.
  `--show-secrets` turns this off. Without `--resolve`, nothing is resolved.
- Nothing else is masked. Error messages can contain values
  ([Trust model](../trust-model/index.md)).
