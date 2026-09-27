# Validation

`validate` checks a loaded config against the schemas of the classes it names, and
raises `ConfigValidationError` at the first problem, naming the key.
`instantiate` runs the same check before it builds anything.

```{literalinclude} ../examples/guide/validation/main.py
:language: python
:caption: main.py
```

```text
Invalid config in `server.workers` (ServerConfig): Value 'many' of type 'str' could not be converted to Integer
`database` expects Database, but the config gives `$class: webapp.cache.RedisCache`.
```

`schema=App` says what the root must build. Every node with `$class` is checked
against its own class's schema, children first, and every object field against the
class it expects, so a cache in the database's place is caught before anything is
built. To test a config without letting the error escape, catch it as above; the
error is a `ValueError` too.

## Files that are incomplete on purpose

`base.yaml` leaves `secret_key` for each environment to fill.
`validate(base, schema=App, allow_missing=True)` accepts the open `???` and still
checks every value the file gives. Without `$class` at its root, `base.yaml` is
checked against the schema of `App`.

## What validation runs

Validation checks values; it is not input sanitisation. It calls no configured
class, but it imports the modules that `$class` and `$ref` name, runs resolvers such
as `oc.env`, and runs the schemas' `default_factory` functions. Validate only
configs you trust. `allowed_modules=["webapp"]` limits which modules a config can
name, as a limit and not a sandbox, and `mask_secrets` hides secrets when you log a
config ([Overrides and environment variables](overrides.md)).

To check files from a terminal, a pre-commit hook or CI, on trusted branches only,
use [`omegakit check`](command-line.md). The full list of checks is in the contracts
under [Validation](../contracts.md#validation).
