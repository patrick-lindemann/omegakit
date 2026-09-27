# Typed configs and validation

## Typed configs

A class that subclasses `Configurable[TConfig]` with a dataclass `TConfig` has a
**schema**. Its config is validated and built into a `TConfig` instance, the typed
config, which `from_config` receives. Every other class, including a bare
`Configurable` and a `TypedDict` or `Mapping` `TConfig`, behaves as in [Instantiation](instantiation.md#instantiation).
`ConfigValidationError` is a `ValueError`.

**Schema lookup.** The schema is the `TConfig` argument found by walking the
original bases of the `$class` and substituting type variables, so
`class Sub(Mixin[int], Model)` and `class Leaf(Mid[Config])` find it. An
unparametrized generic class (`$class: Mid`) uses its type variable's default, or
has no schema. A type variable that cannot be substituted raises `TypeError`.

**Field kinds:**

| Annotation | Config value | Validated by | The typed config holds |
|---|---|---|---|
| **native**: `int`, `float`, `bool`, `str`, `bytes`, `Path`, `Enum`, `Literal` of strings, integers or booleans, `TypedDict`, dataclasses whose fields are all native, `list`/`dict`/`tuple`/`Sequence`/`Mapping` of these, unions of these, and these or `None` | plain values | OmegaConf, then omegakit (see below) | the coerced value |
| **object**: any other class, a generic class, a union of classes, `list`/`dict` of these, and these or `None`, also through a `type` alias | a `$class` or `$ref` node, a list or mapping of them, or `null` if optional | the `$class` against the annotation ([Validation](#validation)), then its own schema | the built object |
| **`Any`** | anything | nothing | the value, with `$class` nodes inside built |

- omegakit behaves the same on every supported OmegaConf. Where OmegaConf 2.3 lacks
  a form (`Literal`, unions with non-scalar members, fixed-length tuples), omegakit
  gives OmegaConf a plain type there and checks the rest itself.
- Enums are given by member **name** or **value** (`kind: B` or `kind: beta`). A
  name wins over an equal value of another member. Values must have the member
  value's exact type: `"2"` and `true` are not the member with value `2`.
- A `Literal` value is first coerced like its type, then compared by type and
  value: `level: "2"` is valid for `Literal[1, 2]`, `level: true` is not.
- Unions: a union may have at most one mapping member (a dataclass, `dict`,
  `Mapping` or `TypedDict`) and at most one list member (`list`, `tuple`,
  `Sequence`); otherwise the lookup raises. A mapping is checked as the mapping
  member, a list as the list member, both with coercion; a scalar must match a
  scalar member's type exactly, without coercion (`"5"` is not an `int`, `True`
  not an `int`, `3` not a `float`, and a string is not a `Path` or an enum member);
  `null` needs `None` in the union.
- `tuple[T, ...]` and `tuple[A, B]` are built as tuples from YAML lists; a
  fixed-length tuple needs exactly that many items. `Sequence` and `Mapping` give
  a `list` and a `dict`.
- A `TypedDict` field is a `dict` whose keys and values are not checked, as in
  OmegaConf.
- Fields with `init=False` and `InitVar` pseudo-fields are not configurable: a
  config key for them is an unknown field. An `InitVar` needs a default.
  Keyword-only fields work like any other.
- In an object `list` or `dict`, every item is a `$class` or `$ref` node, or a
  plain mapping when the item type is a dataclass (a section).
- Missing fields take their dataclass defaults. A field without a default is
  required.
- Schema defaults win over constructor defaults, because the default `from_config`
  passes every field.

**Supported subset.** The lookup raises `ConfigValidationError`, naming the field
and the fix, for:

- `InitVar` fields without a default
- `set`, `frozenset` and the other abstract containers (`Iterable`, `Collection`,
  `Set`, …); use `list`, `tuple` or `Any`
- containers that mix plain values and objects, and tuples, `Sequence` or
  `Mapping` of objects; use `list`, `dict` or `Any`
- unions that mix plain values and classes, and unions with more than one mapping
  or more than one list member
- `Literal` values other than strings, integers and booleans
- annotations that `get_type_hints` cannot resolve, such as names imported under
  `TYPE_CHECKING`
- a dataclass that contains itself, directly or through other dataclasses; the
  error names the cycle (`Tree -> Tree`). A `Configurable` class whose schema has a
  field of that same class is not recursive, because such a field holds an object.

**Per node, in order:**

1. **Lookup** of the schema, as above. Results are cached per class.
2. **Consistency check** (`check_schema`), only when no class in the MRO below
   `Configurable` overrides `from_config`. It runs before any child is built, and a
   successful check is cached:
   - every required `__init__` parameter has a field
   - every field is a keyword parameter, unless `__init__` takes `**kwargs`; a
     field that names a positional-only parameter is rejected even then
   - every field annotation is assignable to its parameter's annotation (`int` to
     `float`, a subclass to its base, unions member by member). Generic
     annotations are skipped, and so is each parameter whose annotation does not
     resolve, such as a type imported under `TYPE_CHECKING`; the other parameters
     are still checked.
3. **Native validation** (parent before children): unknown keys and missing required
   non-native fields raise. The native values are merged onto an OmegaConf structure
   of the native fields, with `Literal` replaced by its value type, and the result
   is checked for literals and converted back into the schema's own classes. Object
   and `Any` values never enter OmegaConf, so resolver-returned objects and object
   defaults work.
4. **Object and `Any` fields** (children before parent) are built as in [Instantiation](instantiation.md#instantiation). A plain
   mapping in a field whose annotation includes a dataclass is a section: it is
   built as that dataclass, with the same steps. The type of a built object is not
   checked; the `$class` was checked before building ([Validation](#validation)), and what `from_config`
   returns is its own contract.
5. **Assembly:** `TConfig(**fields)`, so `__post_init__` runs. Nested native
   dataclasses, including those in `list` and `dict` fields, are the user's classes.
6. **Call:** `from_config(typed_config)`, or a partial of it for `prepare` and
   `$partial` that passes call-time arguments as `**kwargs`. Validation happens when
   the partial is created; a `???` never reaches it.

Validation errors name the node path and the schema class. The whole node is
validated before any configured target is built ([Instantiation](instantiation.md#instantiation)), so a config error never
leaves some children built.

**`from_config` contract.** It receives the typed config with its children built,
plus `**kwargs` from a partial or a direct caller. It returns `Self`, or is
annotated with a base class when it returns a subclass instance (a factory). Direct
calls with a raw mapping still work, but are outside the contract.

**`make_node(target, **kwargs)`** returns `{"$class": "<module>.<qualname>", **kwargs}`
for a class or function defined at module level, for children that code chooses
inside `from_config`. Such children cannot be reached by overrides. Children that
users should configure belong in object fields.

## Validation

`validate(config, *, schema=None, allow_missing=False, allowed_modules=None)`
checks a config that
`load_config` has assembled. It returns nothing and raises `ConfigValidationError`
at the first problem.

1. `load_config` assembles the full config ([Pipeline](assembly.md#pipeline)). It checks no schema.
2. `validate` checks the assembled config, or any node of it.
3. `instantiate` and `prepare` run the same check on the node they build before
   building it ([Instantiation](instantiation.md#instantiation)).

The check:

- The config is resolved first. An interpolation that fails, and a `???` anywhere,
  make the config invalid (unless `allow_missing`). The error names the full key.
- Every node with `$class` is checked against the schema of its class ([Typed configs](#typed-configs)),
  children before parents. `$class` is imported to find the schema, but the class
  is not called. Classes without a schema only have their children checked.
- `schema` is the class the root must match:
  - A dataclass makes the root a section: unknown keys, invalid plain values and
    missing required fields raise, and so do nested dataclass sections.
  - Another class makes the root a node that builds it. With `$class`, that class
    must be `schema` or a subclass, and is checked as usual. Without `$class`, the
    root is checked against the schema of `schema`, as a fragment file that is
    completed elsewhere; a class without a dataclass schema raises.
  - A `schema` that is not a class raises `TypeError`.
  - Without `schema`, the root is not checked, but its `$class` nodes are.
- `allow_missing=True` accepts missing values: `???`, required fields that are not
  given, and interpolations to missing or unknown keys (as in a library file that
  its consumers complete). Every value that is given is still checked.
- An object field ([Typed configs](#typed-configs)) accepts a node whose `$class` is the annotated class or a
  subclass, a `$ref` to an instance of it, or `None` when the annotation is
  optional. A mapping without `$class` is accepted only when the annotation is a
  dataclass, which is then checked as a section. The class check is skipped when
  `$class` names a function, when the node has `$partial: true`, and when the
  annotation is not a plain class or a union of plain classes, such as a
  `Callable` or a `Protocol`. The value's reserved keys and nested `$class` and
  `$ref` nodes are still checked.
- `Any` fields are not checked, but their `$class` nodes are.
- What `from_config` returns is not checked. A valid config is one whose every
  node matches its schema; building it is left to `from_config`.
- Reserved keys ([Reserved keys](instantiation.md#reserved-keys)) are checked, and `$meta` is ignored.
- A `$class` or `$ref` that is not a string, is not a dotted path, names a module
  that does not exist (or whose parent package does not exist), or names a missing
  attribute raises, naming the node. So does a `$class` target that is neither
  callable nor has `from_config`; `$ref` accepts any object. An `ImportError` that
  the named module raises while it is imported, such as one for a missing
  dependency, propagates with its own type.
- `check_schema` ([Typed configs](#typed-configs)) runs for every class with a schema.
- Plain values are checked the way `instantiate` coerces them, so `"64"` is a valid
  `int`. The config itself is not changed.

What runs during validation. The check looks at values: it calls no `$class`
target and no `from_config`, and it constructs none of the schema's dataclasses, so
their `__post_init__` does not run. `instantiate` constructs them once, while
building. Code still runs:

- the modules named by `$class` and `$ref` are imported, with their import-time
  code;
- resolvers run;
- `__instancecheck__` and `__subclasscheck__` of imported classes run;
- every `default_factory` of a schema runs, possibly several times and even for
  fields that the config sets, together with the hooks of whatever it constructs.
  An exception from a factory propagates with its own type.

### Allowed modules

`validate`, `instantiate` and `prepare` take `allowed_modules`, which limits the
modules that `$class` and `$ref` may name. It is not a sandbox.

- `None`, the default, allows every module. `[]` allows none. Any iterable of
  module names is accepted and read once; a plain string raises `TypeError`.
- An entry allows that module and its submodules: `["webapp", "torch.optim"]`
  allows `webapp.db.Postgres` and `torch.optim.Adam`, but not `webapp_evil.X` or
  `torch.load`. An entry that names a class does not allow it. A `$ref` to a
  value such as `math.pi` needs `"math"`.
- Two checks, for `$class` and `$ref` alike, on every node that the validation walk
  reaches, including nodes under `Any`, `Callable`, `list` and `dict` fields:
  1. Before the import, the module part of the path must be allowed, so a module
     that is not allowed is never imported. The parent packages of an allowed
     module are still imported: `torch.optim` imports `torch`.
  2. After the import, the object's `__module__`, when it has one, must be
     allowed. This rejects a name that an allowed module imported from elsewhere,
     such as `pkgx.db.run` for `from subprocess import run`, and accepts
     re-exports inside an allowed package. An instance reports the module of its
     class.
- A path that fails either check raises `ConfigValidationError`, naming the path
  and the node.
- Allowing `builtins`, `importlib`, `os`, `subprocess`, `shutil` or `pickle` is
  the same as no restriction: `$class: builtins.__import__` imports any module, and
  `builtins.open` truncates files.
- Not covered: resolvers, the `schema` argument and `--schema`, `json-schema`
  import paths, and `instantiate` calls made inside your own `from_config`.
