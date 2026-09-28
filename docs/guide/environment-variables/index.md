# Environment variables

A config reads environment variables through OmegaConf's `oc.env` resolver. It is
built into OmegaConf, so it works without any registration. The data directory
can differ between machines, and on a cluster, a job array can pick each run's
seed from the task number:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```{code-block} text
:caption: Output

config.data_dir: data
config.seed: 0
config.data_dir: /datasets/sine
config.seed: 3
type(config.seed): int
```

Without the variables, the defaults after the commas applied. The variables were
set after `load_config`, and the config still saw them. `oc.decode` made the seed
the integer 3, not the string `"3"`.

For a secret, such as a token, use `${secret:NAME}` instead, which keeps it out of
printed configs ([Secrets](../../security/secrets/index.md)). omegakit does not read
`.env` files. Load them with a tool such as `python-dotenv` before loading the
config.

## Rules

- `${oc.env:NAME}` reads the variable `NAME` when the value is resolved
  ([Loading](../loading/index.md#rules) says when that is), and
  `${oc.env:NAME,default}` falls back to `default`. The value is a string;
  `${oc.decode:${oc.env:NAME}}` parses it as YAML.
- A variable that is not set and has no default fails like any interpolation
  ([Interpolation](../interpolation/index.md#rules)), also with
  `allow_missing=True`.
