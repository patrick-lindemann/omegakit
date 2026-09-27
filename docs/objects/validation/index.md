# Validation

`validate` checks a loaded config against the schemas of the classes it names, and
raises `ConfigValidationError` at the first problem, naming the key.
`instantiate` runs the same check before it builds anything.

```{literalinclude} main.py
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
modules a config can name with `allowed_modules` ([Trust model](../../security/trust-model/index.md)).

To check files from a terminal, a pre-commit hook or CI, use
[`omegakit check`](../../tools/command-line/index.md).

## Rules

`validate(config, *, schema=None, allow_missing=False, allowed_modules=None)`
checks an assembled config, or any node of it, and raises `ConfigValidationError`
at the first problem. `load_config` checks no schema. `instantiate` and `prepare`
run this check, with their own `schema`, before building.

- The config is resolved first. A failing interpolation or a `???` is invalid
  unless `allow_missing`. The error names the full key.
- Every `$class` node is checked against its class's schema. Nested `$class`
  nodes are checked before their parent. The class is imported, not called. A
  class without a schema has only its children checked.
- `schema` says what the root must match. A dataclass checks the root as a
  section. A class checks the root's `$class`, which must be that class or a
  subclass. When the root has no `$class`, it is checked against the class's own
  schema, as a fragment; a class without one raises. Anything that is not a class
  raises `TypeError`. Without `schema`, only the `$class` nodes are checked.
- `allow_missing=True` accepts `???`, required fields that are not given, and
  interpolations to missing or unknown keys. Given values are still checked.
- An object field accepts a `$class` node of the annotated class or a subclass, a
  `$ref` to an instance, or `null` if optional. It accepts a plain mapping only if
  the annotation is a dataclass (a section). The class check is skipped for
  functions, for `$partial: true`, and for annotations that are not plain classes
  or unions of them, such as `Callable` and `Protocol`. Reserved keys and nested
  nodes are still checked. Any other value raises `ConfigValidationError` naming
  the field, the expected class and what the config gives.
- Reserved keys are checked, and `$meta` is ignored. What `from_config` returns is
  not checked.
- `$class` or `$ref` raises `ConfigValidationError`, naming the node, when it is
  not a string or not a dotted path, or names a missing module (or parent package)
  or attribute. The `ImportError` is its `__cause__`. So does
  a `$class` target that is neither callable nor has `from_config`; `$ref` accepts
  any object. An `ImportError` raised by the named module itself, such as for a
  missing dependency, propagates.
- Plain values are checked as `instantiate` converts them: `"64"` is a valid
  `int`. The config is not changed.
- `allowed_modules` limits which modules `$class` and `$ref` may name
  ([Restricting imports](../../security/restricting-imports/index.md#allowed-modules)).

**What runs.** No `$class` target, `from_config` or schema dataclass is called;
their `__post_init__` runs once, when building. But the modules named by `$class`
and `$ref` are imported, resolvers run, the `__instancecheck__` and
`__subclasscheck__` of imported classes run, and every `default_factory` runs,
possibly several times and also for fields the config sets. A factory's exception
propagates.
