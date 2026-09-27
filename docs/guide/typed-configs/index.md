# Typed configs

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

## Field kinds

The application's schema shows the three kinds of field:

```{literalinclude} ../../webapp/webapp/__init__.py
:language: python
:caption: webapp/__init__.py (excerpt)
:pyobject: AppConfig
```

- **Values:** `int`, `float`, `bool`, `str`, `Path`, enums, `Literal`, dataclasses
  of these, and `list`, `dict`, `tuple` or unions of these, such as `log_dir`.
  They are converted and checked like `port` above.
- **Objects:** any other class, such as `server: Server` or `jobs: dict[str, Job]`.
  The config holds a `$class` node of that class or a subclass, or a `$ref` to an
  instance, and the typed config holds the built object. `database: Database`
  accepts both `Postgres` and `SQLite`.
- **`Any`:** the value is not checked, but `$class` nodes and reserved keys inside
  it are. `JobConfig.handler` is `Any`, because it holds a function.

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
([Building objects](../building-objects/index.md#rules)).

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
config, which `from_config` receives. Any other class, including a bare
`Configurable` or one with a `TypedDict` or `Mapping` `TConfig`, is built as in
[Building objects](../building-objects/index.md#rules).

**Schema lookup.** The `TConfig` argument is found by walking the original bases
of the `$class` and substituting type variables, so `class Sub(Mixin[int], Model)`
and `class Leaf(Mid[Config])` work. An unparametrized generic class uses its type
variable's default, or has no schema. A type variable that cannot be substituted
raises `TypeError`. The result is cached per class.

**Field kinds.**

| Annotation | Config value | Checked by | Typed config holds |
|---|---|---|---|
| **native**: `int`, `float`, `bool`, `str`, `bytes`, `Path`, `Enum`, `Literal` of `str`, `int` or `bool`, `TypedDict`, dataclasses whose fields are all native, `list`, `dict`, `tuple`, `Sequence` and `Mapping` of these, and unions of these, optional or not | plain values | OmegaConf, then omegakit | the converted value |
| **object**: any other class, generic classes, unions of classes, `list` or `dict` of these, optional or not, also through a `type` alias | a `$class` or `$ref` node, a list or mapping of them, or `null` if optional | the class check ([Validation](../validation/index.md#rules)), then the node's own schema | the built object |
| **`Any`** | anything | not checked, but `$class` nodes inside are | the value, with `$class` nodes built |

- Behaviour does not depend on the OmegaConf version.
- Enums accept a member name or value (`kind: B`, `kind: beta`). A name wins over
  an equal value of another member, and a value needs the exact type of the
  member's value.
- A `Literal` value is converted like its type, then compared by type and value:
  `"2"` is valid for `Literal[1, 2]`, `true` is not.
- A union has at most one mapping member (dataclass, `dict`, `Mapping`,
  `TypedDict`) and one list member (`list`, `tuple`, `Sequence`). A mapping or a
  list is checked, with conversion, as that member. A scalar must match a scalar
  member's type exactly: `"5"` is not an `int`, `True` is not an `int`, `3` is not
  a `float`, and a string is not a `Path` or an enum. `null` needs `None` in the
  union.
- Tuples come from lists, and `tuple[A, B]` needs exactly two items. `Sequence`
  and `Mapping` give a `list` and a `dict`. A `TypedDict` field is an unchecked
  `dict`.
- `init=False` fields and `InitVar`s are not configurable: a key for them is
  unknown. An `InitVar` needs a default.
- Items of an object `list` or `dict` are `$class` or `$ref` nodes, or plain
  mappings when the item type is a dataclass (a section).
- An absent field takes its dataclass default. A field without one is required.
  Schema defaults win over constructor defaults.

**Unsupported**, raising `ConfigValidationError` that names the field and the fix:
an `InitVar` without a default; `set`, `frozenset` and other abstract containers;
a container that mixes values and objects; a `tuple`, `Sequence` or `Mapping` of
objects; a union that mixes values and classes, or has two mapping or two list
members; `Literal` values other than `str`, `int` and `bool`; an annotation that
`get_type_hints` cannot resolve, such as a name imported under `TYPE_CHECKING`; a
dataclass that contains itself, directly or indirectly (the error names the cycle,
`Tree -> Tree`). A `Configurable` whose schema has a field of its own class is not
recursive: that field holds an object.

**Per node, in order:**

1. Look up the schema.
2. Run `check_schema`, unless a class in the MRO below `Configurable` overrides
   `from_config`. It is cached once it passes. Every required `__init__` parameter
   needs a field. Every field must be a keyword parameter, unless `__init__` takes
   `**kwargs`; a positional-only parameter is rejected even then. Every field's
   annotation must be assignable to its parameter's: `int` to `float`, a subclass
   to its base, unions member by member. Generic annotations are skipped, and so
   is each parameter whose annotation does not resolve.
3. Check the native fields, parent before children. An unknown key and a missing
   required field raise. Native values are checked through OmegaConf and
   converted into the schema's own types. Object and `Any` values never enter
   OmegaConf.
4. Build the object and `Any` fields, children first, as in
   [Building objects](../building-objects/index.md#rules). A plain mapping in a field
   annotated with a dataclass is a section, built the same way. A built object's
   type is not checked again.
5. Call `TConfig(**fields)`, so `__post_init__` runs.
6. Call `from_config(typed_config)`, or build a partial of it that passes
   call-time arguments as `**kwargs`.

The whole node is validated before anything configured is built, so an error never
leaves some children built. Errors name the node path and the schema class.

**`from_config`** receives the typed config, children built, plus `**kwargs` from a
partial or a caller. It returns `Self`, or is annotated with a base class when it
returns a subclass. Calling it with a raw mapping works but is outside the rules.

**`make_node(target, **kwargs)`** returns `{"$class": "<module>.<qualname>",
**kwargs}` for a module-level class or function, for children that code chooses
in `from_config`. Overrides cannot reach such children.
