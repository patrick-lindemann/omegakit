# Overrides and environment variables

Overrides change values after a config is assembled, and win over everything in the
files. Environment variables come in through OmegaConf's `oc.env` resolver.

```{literalinclude} ../examples/guide/overrides/main.py
:language: python
:caption: main.py
```

```text
9000 4
1
s3cr3t-from-the-vault
```

## Overrides

A list of `key=value` strings is what a command line gives you, so `webapp`'s
entrypoint passes `sys.argv[1:]` straight to `load_config`. Values are read as YAML:
`server.port=9000` is an integer. A nested `dict` does the same from code; the
tests use one to put an in-memory database under `database`.

`instantiate` and `prepare` take `overrides=` too. They merge them into a copy of the
node they build and leave the config you passed unchanged.

Overrides arrive after the files are assembled, so an `~import`, `$base` or
`$defaults` inside an override stays literal. They carry the same trust as the
files, so never build them from untrusted input ([Security](../security.md)).

## Environment variables

`${oc.env:NAME}` reads the variable `NAME` when the value is resolved, and
`${oc.env:NAME,default}` falls back to a default. It is built into OmegaConf, so it
works without any registration. `webapp` uses it twice: the root file picks the
environment with `${oc.env:APP_ENV,dev}`, and production reads its secret key with
`${oc.env:SECRET_KEY}`. A variable that is not set and has no default raises
`ConfigValidationError` when the value is validated or built.

omegakit does not read `.env` files; load them with a tool such as `python-dotenv`
before loading the config.

A resolved config holds the real secret, as the third line of the output shows. To
log a config with its secrets masked, see
[Logging without secrets](../security.md#logging-without-secrets).

## Rules

- `overrides` is a `DictConfig`, a `dict`, or a list of `key=value` strings. Any
  other type, including a `ListConfig`, raises `TypeError`.
- Each value in a list is parsed as YAML: `port=9000` is an integer, `tags=[a, b]`
  a list. A string without `=`, such as `a`, sets `a` to `null`.
- An override that does not parse, has a value OmegaConf does not support, or is
  rejected by a struct config raises `ConfigValidationError` from `load_config`,
  `instantiate` and `prepare`, naming the override or its key.
- Overrides are merged after assembly. An `~import`, `$base` or `$defaults` in an
  override stays literal, and `$meta` and construction keys in one are stripped
  like any other.
- Overrides win over every value from the files
  ([Precedence](loading.md#rules)). `instantiate` and `prepare` merge theirs into
  a copy of the node and leave the config passed in unchanged.
