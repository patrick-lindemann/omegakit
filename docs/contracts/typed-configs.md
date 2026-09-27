# Typed configs and validation

## Typed configs

A class that subclasses `Configurable[TConfig]` with a dataclass `TConfig` has a
**schema**: its config is validated and built into a `TConfig` instance, the typed
config, which `from_config` receives. Any other class, including a bare
`Configurable` or a `TypedDict` or `Mapping` `TConfig`, is built as in
[Building objects](../guide/building-objects.md#rules). `ConfigValidationError` is a
`ValueError`.

**Schema lookup.** The `TConfig` argument is found by walking the original bases of
the `$class`, substituting type variables (`class Sub(Mixin[int], Model)`,
`class Leaf(Mid[Config])`). An unparametrized generic class uses its type
variable's default, or has no schema; a type variable that cannot be substituted
raises `TypeError`. Results are cached per class.

**Field kinds:**

| Annotation | Config value | Checked by | Typed config holds |
|---|---|---|---|
| **native**: `int`, `float`, `bool`, `str`, `bytes`, `Path`, `Enum`, `Literal` of `str`/`int`/`bool`, `TypedDict`, all-native dataclasses, `list`/`dict`/`tuple`/`Sequence`/`Mapping` and unions of these, optional or not | plain values | OmegaConf, then omegakit | the converted value |
| **object**: any other class, generic classes, unions of classes, `list`/`dict` of these, optional or not, also through a `type` alias | a `$class` or `$ref` node, a list or mapping of them, `null` if optional | the class check ([Validation](#validation)), then the node's own schema | the built object |
| **`Any`** | anything | not checked; `$class` nodes inside are | the value, with `$class` nodes built |

- Behaviour is the same on every supported OmegaConf; where 2.3 lacks a form
  (`Literal`, unions with non-scalar members, fixed-length tuples), omegakit checks
  it itself.
- Enums: by member name or value (`kind: B`, `kind: beta`); a name wins over an
  equal value of another member; a value needs the member value's exact type.
- `Literal`: converted like its type, then compared by type and value
  (`"2"` is valid for `Literal[1, 2]`, `true` is not).
- Unions: at most one mapping member (dataclass, `dict`, `Mapping`, `TypedDict`) and
  one list member (`list`, `tuple`, `Sequence`). A mapping or list is checked, with
  conversion, as that member; a scalar must match a scalar member's type exactly
  (`"5"` is not an `int`, `True` not an `int`, `3` not a `float`, a string not a
  `Path` or an enum); `null` needs `None` in the union.
- Tuples come from lists; `tuple[A, B]` needs exactly two items. `Sequence` and
  `Mapping` give a `list` and a `dict`. A `TypedDict` field is an unchecked `dict`.
- `init=False` fields and `InitVar`s are not configurable (a key for them is
  unknown); an `InitVar` needs a default.
- Items of an object `list` or `dict` are `$class` or `$ref` nodes, or plain mappings
  when the item type is a dataclass (a section).
- Absent fields take their dataclass defaults; a field without one is required.
  Schema defaults win over constructor defaults.

**Unsupported,** raising `ConfigValidationError` that names the field and the fix:
`InitVar` without a default; `set`, `frozenset` and other abstract containers;
containers mixing values and objects, and tuples, `Sequence` or `Mapping` of
objects; unions mixing values and classes, or with two mapping or two list members;
`Literal` values other than `str`, `int`, `bool`; annotations that
`get_type_hints` cannot resolve (names imported under `TYPE_CHECKING`); a dataclass
that contains itself, directly or indirectly (the error names the cycle,
`Tree -> Tree`). A `Configurable` whose schema has a field of its own class is not
recursive: that field holds an object.

**Per node, in order:**

1. Look up the schema.
2. `check_schema`, unless a class in the MRO below `Configurable` overrides
   `from_config`; cached once it passes. Every required `__init__` parameter needs a
   field; every field must be a keyword parameter, unless `__init__` takes
   `**kwargs` (a positional-only parameter is rejected even then); every field's
   annotation must be assignable to its parameter's (`int` to `float`, subclass to
   base, unions member by member). Generic annotations are skipped, and so is each
   parameter whose annotation does not resolve.
3. Native fields, parent before children: unknown keys and missing required
   non-native fields raise; native values are checked through OmegaConf and
   converted into the schema's own types. Object and `Any` values never enter
   OmegaConf.
4. Object and `Any` fields, children first, are built as in
   [Building objects](../guide/building-objects.md#rules); a plain mapping in a field
   annotated with a dataclass is a section, built the same way. A built object's
   type is not checked again.
5. `TConfig(**fields)`, so `__post_init__` runs.
6. `from_config(typed_config)`, or a partial of it that passes call-time arguments
   as `**kwargs`.

The whole node is validated before anything configured is built, so an error never
leaves some children built. Errors name the node path and the schema class.

**`from_config`** receives the typed config, children built, plus `**kwargs` from a
partial or a caller. It returns `Self`, or is annotated with a base class when it
returns a subclass (a factory). Calling it with a raw mapping works but is outside
the contract.

**`make_node(target, **kwargs)`** returns
`{"$class": "<module>.<qualname>", **kwargs}` for a module-level class or function,
for children that code chooses in `from_config`. Overrides cannot reach them.

## Validation

`validate(config, *, schema=None, allow_missing=False, allowed_modules=None)`
checks an assembled config, or any node of it, and raises `ConfigValidationError`
at the first problem. `load_config` checks no schema; `instantiate` and `prepare`
run this check before building.

- The config is resolved first; a failing interpolation or a `???` is invalid
  unless `allow_missing`. The error names the full key.
- Every `$class` node is checked against its class's schema, children first. The
  class is imported, not called. A class without a schema has only its children
  checked.
- `schema` is what the root must match. A dataclass checks the root as a section.
  Another class: with a root `$class`, it must be `schema` or a subclass; without,
  the root is checked against `schema`'s schema, as a fragment (a class without a
  dataclass schema raises). A non-class raises `TypeError`. Without `schema`, only
  the `$class` nodes are checked.
- `allow_missing=True` accepts `???`, required fields that are not given, and
  interpolations to missing or unknown keys; given values are still checked.
- An object field accepts a `$class` node of the annotated class or a subclass, a
  `$ref` to an instance, or `null` if optional; a plain mapping only if the
  annotation is a dataclass (a section). The class check is skipped for functions,
  `$partial: true`, and annotations that are not plain classes or unions of them
  (`Callable`, `Protocol`); reserved keys and nested nodes are still checked.
- Reserved keys are checked, and `$meta` is ignored. What `from_config` returns is
  not checked.
- `$class` or `$ref` raises, naming the node, when it is not a string or not a
  dotted path, or names a missing module (or parent package) or attribute; so does a
  `$class` target that is neither callable nor has `from_config` (`$ref` accepts any
  object). An `ImportError` raised by the named module itself, such as for a missing
  dependency, propagates.
- Plain values are checked as `instantiate` converts them (`"64"` is a valid `int`).
  The config is not changed.

**What runs.** No `$class` target, `from_config` or schema dataclass is called; their
`__post_init__` runs once, when building. But modules named by `$class` and `$ref`
are imported, resolvers run, imported classes' `__instancecheck__` and
`__subclasscheck__` run, and every `default_factory` runs, possibly several times and
for fields the config sets. A factory's exception propagates.

### Allowed modules

`validate`, `instantiate` and `prepare` take `allowed_modules`. It limits which
modules `$class` and `$ref` may name; it is not a sandbox.

- `None` (default) allows all, `[]` none. Any iterable of module names, read once; a
  `str` raises `TypeError`.
- An entry allows that module and its submodules: `["webapp", "torch.optim"]` allows
  `webapp.db.Postgres` and `torch.optim.Adam`, not `webapp_evil.X` or `torch.load`.
  An entry naming a class allows nothing. `$ref: math.pi` needs `"math"`.
- Checked on every node the walk reaches, including under `Any`, `Callable`,
  `list` and `dict` fields: before importing, the module part of the path (parent
  packages are still imported); after importing, the object's `__module__`, if it
  has one. The second check rejects names an allowed module imported from
  elsewhere (`pkgx.db.run` for `from subprocess import run`) and accepts
  re-exports within an allowed package; an instance reports its class's module.
- A failing path raises `ConfigValidationError` naming the path and node.
- Allowing `builtins`, `importlib`, `os`, `subprocess`, `shutil` or `pickle` equals
  no restriction (`builtins.__import__`, `builtins.open`).
- Not covered: resolvers, `schema` and `--schema`, `json-schema` paths, and
  `instantiate` calls inside your own `from_config`.
