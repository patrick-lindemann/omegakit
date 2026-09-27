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
{'$class': 'webapp.server.Server', 'host': '0.0.0.0', 'port': 8000, 'workers': 8, 'secret_key': '***'}
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
files: an override can set `$class` or read an environment variable, so never build
overrides from requests or other untrusted input.

## Environment variables

`${oc.env:NAME}` reads the variable `NAME` when the value is resolved, and
`${oc.env:NAME,default}` falls back to a default. It is built into OmegaConf, so it
works without any registration. `webapp` uses it twice: the root file picks the
environment with `${oc.env:APP_ENV,dev}`, and production reads its secret key with
`${oc.env:SECRET_KEY}`. A variable that is not set and has no default raises
`ConfigValidationError` when the value is validated or built.

omegakit does not read `.env` files; load them with a tool such as `python-dotenv`
before loading the config.

## Logging a config without its secrets

A resolved config holds the real secret, as the third line of the output shows, and
so do the objects built from it. Log `mask_secrets(config)` instead: it resolves the
config and replaces with `***` the values under keys such as `secret_key`,
`password` or `token`, the values read from variables such as `SECRET_KEY`, and those
secrets wherever they appear inside other strings, such as a database URL.
`mask_secrets(config, keys=["salt"])` adds your own words. `omegakit show` masks the
same way.

Masking is a safety net, not a guarantee: a secret under a key that names no secret,
or one read by another resolver, is not masked. The rules are in the contracts under
[Masking secrets](../contracts/environment.md#masking-secrets), and
[Precedence](../contracts/assembly.md#precedence) places overrides among the other sources.
