# Environment variables

A config reads environment variables through OmegaConf's `oc.env` resolver. It is
built into OmegaConf, so it works without any registration. On a cluster, a job
array can pick each run's seed from the task number:

```{literalinclude} array.yaml
:language: yaml
:caption: array.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
0 runs/poly3-adam/seed0
3 runs/poly3-adam/seed3
```

Without `SLURM_ARRAY_TASK_ID`, the default `0` applies. `oc.env` gives a string, and
`oc.decode` parses it as YAML, so the seed is the integer 3. That matters where the
value is used as it is: `random.seed("3")` seeds differently from `random.seed(3)`.

The variable is read when the value is resolved, not while loading. For a secret,
such as a token, use `${secret:NAME}` instead, which keeps it out of printed
configs ([Secrets](../../security/secrets/index.md)). omegakit does not read `.env`
files. Load them with a tool such as `python-dotenv` before loading the config.

## Rules

- `${oc.env:NAME}` reads the variable `NAME` when the value is resolved, and
  `${oc.env:NAME,default}` falls back to `default`. The value is a string;
  `${oc.decode:${oc.env:NAME}}` parses it as YAML.
- In an `~import` path, and in the values of `$base` and `$defaults`, the variable
  is read while loading ([Loading](../loading/index.md#rules)). Everywhere else it
  is read when the value is read, validated or built.
- A variable that is not set and has no default fails like any interpolation
  ([Interpolation](../interpolation/index.md#rules)), also with
  `allow_missing=True`.
