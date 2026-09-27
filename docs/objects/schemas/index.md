# Schemas

A class that subclasses `Configurable[TConfig]`, with a dataclass `TConfig`, has a
schema. Its config is checked against the dataclass before any object is built, and
the class receives the checked values, with the right types for your editor.
Classes without a schema keep working as plain `$class` targets.

`webapp`'s server is the simplest case:

```{literalinclude} ../../webapp/webapp/server.py
:language: python
:caption: webapp/server.py
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
9000 1
RedisCache 600
MemoryCache
EmailNotifier
```

`port: "9000"` became the integer 9000, and `workers` took its default. A key the
schema does not have, or a value it cannot convert, raises `ConfigValidationError`
naming the key. `check_schema(Server)` checks that the schema fits the constructor:
every required parameter has a field, and every field is a parameter of a matching
type. It runs by itself whenever the class is validated or built; call it in a test
to catch a mismatch without a config.

The kinds of field a schema can have, and how each is checked, are on
[Dataclass schemas](../../schemas/dataclass-schemas/index.md).

## A custom `from_config`

`from_config` receives the typed config, with object fields already built, and
calls the constructor. The default passes every field. Override it when the config
and the constructor differ, as the cache does with its `ttl`:

```{literalinclude} ../../webapp/webapp/cache.py
:language: python
:caption: webapp/cache.py
```

Keep `**kwargs` in the signature: arguments given to a partial from `prepare` arrive
there. Any class with a `from_config` classmethod works the same
([Instantiation](../instantiation/index.md#rules)).

Children that code chooses, rather than the user, are created with `make_node`.
`App.from_config` builds an in-memory cache when the config has none, which is why
`cache=null` gave a `MemoryCache` above:

```{literalinclude} ../../webapp/webapp/__init__.py
:language: python
:pyobject: App.from_config
```

## Factories

A `from_config` that returns a subclass annotates the base class as its return
type, since `Self` would claim the class it was called on:

```{literalinclude} notify.py
:language: python
:caption: notify.py
```

A `TypedDict` `TConfig` gives `from_config` static types only: it receives a plain
`dict`, and the field values are not checked, though `$class` nodes inside are.

## Rules

A class that subclasses `Configurable[TConfig]` with a dataclass `TConfig` has a
**schema**. Its config is validated and built into a `TConfig` instance, the typed
config, which `from_config` receives. A dataclass that is not a `Configurable` is
its own schema ([Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules)).
Any other class, including a bare `Configurable` or one with a
`TypedDict` or `Mapping` `TConfig`, is built as in
[Instantiation](../instantiation/index.md#rules).

**Schema lookup.** The `TConfig` argument is found by walking the original bases
of the `$class` and substituting type variables, so `class Sub(Mixin[int], Model)`
and `class Leaf(Mid[Config])` work. An unparametrized generic class uses its type
variable's default, or has no schema. A type variable that cannot be substituted
raises `TypeError`. The result is cached per class.

**Field kinds**, supported annotations and defaults are as in
[Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules).

**Per node, in order:**

1. Look up the schema.
2. Run `check_schema`, unless the class is a dataclass that is its own schema, or a
   class in the MRO below `Configurable` overrides `from_config`. It is cached once it passes. Every required `__init__` parameter
   needs a field. Every field must be a keyword parameter, unless `__init__` takes
   `**kwargs`; a positional-only parameter is rejected even then. Every field's
   annotation must be assignable to its parameter's: `int` to `float`, a subclass
   to its base, unions member by member. Generic annotations are skipped, and so
   is each parameter whose annotation does not resolve. A mismatch raises
   `ConfigValidationError` naming the field or parameter.
3. Check the native fields, parent before children, as in
   [Dataclass schemas](../../schemas/dataclass-schemas/index.md#rules).
4. Build the object and `Any` fields, children first, as in
   [Instantiation](../instantiation/index.md#rules). A plain mapping in a field
   annotated with a dataclass is a section, built the same way. A built object's
   type is not checked again.
5. Call `TConfig(**fields)`, so `__post_init__` runs.
6. Call `from_config(typed_config)`, or build a partial of it that passes
   call-time arguments as `**kwargs`.

A dataclass that is its own schema skips steps 5 and 6: the class is called with
the fields, or a partial of it is built.

The whole node is validated before anything configured is built, so an error never
leaves some children built. Errors name the node path and the schema class.

**`from_config`** receives the typed config, children built, plus `**kwargs` from a
partial or a caller. It returns `Self`, or is annotated with a base class when it
returns a subclass. Calling it with a raw mapping works but is outside the rules.

**`make_node(target, **kwargs)`** returns `{"$class": "<module>.<qualname>",
**kwargs}` for a module-level class or function, for children that code chooses
in `from_config`. Overrides cannot reach such children. A target defined inside a
function or a class raises `ValueError`, because it cannot be imported by its
path.
