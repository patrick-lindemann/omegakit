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

Validation calls no configured class, but it imports the modules that `$class` and
`$ref` name and runs every resolver. Validate only configs you trust, and limit the
modules a config can name with `allowed_modules` ([Security](../security.md)).

To check files from a terminal, a pre-commit hook or CI, use
[`omegakit check`](command-line.md). The full list of checks is in the contracts
under [Validation](../contracts/typed-configs.md#validation).
