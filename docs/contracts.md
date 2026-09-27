# Configuration contracts

This page is the normative description of the omegakit configuration language.

## Pipeline

`load_config` assembles a file in this order:

1. Parse the YAML file.
2. Resolve `~import` depth-first. Each imported file resolves its own imports before
   it is inserted. No `$base` is merged during this step.
3. Merge `$base`, children before parents.
4. Apply `$defaults`, children before parents.
5. Merge the overrides.
6. Strip `$meta` (unless `keep_meta=True`) and the construction keys `$class`,
   `$ref` and `$partial` (if `keep_targets=False`).

Overrides cannot introduce `~import`, `$base` or `$defaults`: they arrive after
assembly, so these keys and values stay literal. `$meta` and construction keys
introduced by overrides are stripped like any other.

## Precedence

From strongest to weakest:

1. Overrides.
2. The node's own keys.
3. Later items of a list-valued `$base`.
4. Earlier items of a list-valued `$base`.

`$defaults` is weaker than the item it is applied to. Because `$defaults` is
applied children before parents, an inner `$defaults` has already been merged into
an item when an outer `$defaults` is merged underneath it, so the inner one wins.

`$defaults` applies only to the dict-valued siblings in its own mapping. Scalars,
lists and `$`-prefixed siblings are untouched, and grandchildren are reached only
through the merged sibling's own keys.

## Resolution timing

Only structural references are resolved during assembly:

- the path of an `~import`, including `${…}` inside it
- the value of `$base`
- the value of `$defaults`

An `~import` path is resolved against its own file as parsed: it sees resolvers
and the keys literally present in that file. It does not see keys contributed by a
`$base`, by another file, or by overrides.

A `$base` or `$defaults` value that is an interpolation (`$base: ${_common}`) sees
the referenced node with its own `$base` and `$defaults` already merged. Nodes are merged children before parents and
in dependency order:

- A node waits while its value refers to a node that still has an unmerged `$base`
  (or unapplied `$defaults`), or to a key that does not exist yet, such as a key
  that a later `$base` creates. It is merged as soon as the referenced node is.
- An ancestor of a waiting node waits too.
- References that can never be merged raise `ConfigValidationError`: a key that
  never appears (caused by the interpolation error), and nodes that refer to each
  other (`references form a cycle`), naming the nodes.
- All bases are merged before any defaults are applied, so a `$base` sees a node
  without the keys that its parent's `$defaults` add later.

A `${…}` base is a copy taken when it is merged, so it has three limits:

- It cannot refer to keys that an enclosing node's own `$base` brings in. With
  `$base: ~import common.yaml` at the root of a file, `replica: {$base: ${db}}`
  raises when `db` comes from `common.yaml`.
- Inside a file that another file uses as its `$base`, it is merged in that file,
  before the using file's own keys apply. A `replica` in `lib.yaml` that copies
  `lib.yaml`'s `db` keeps that copy when the using file replaces `db`.
- Overrides arrive after assembly, so an override of the referenced node does not
  reach the copy: `db.pool=9` leaves `replica.pool` as it was.

A relative reference (`${..db}`) finds a sibling wherever the file ends up, so a
`${…}` base placed next to the node it copies, in the file that defines both, copies
that file's value even when the file is itself used as a `$base` or imported.

Every other `${…}` stays an interpolation until it is accessed or instantiated, and
then resolves against the assembled config. This includes interpolations inside
imported files and inside `$base` and `$defaults` values. A relative interpolation
such as `${.id}` resolves at the node's final position.

`instantiate` and `prepare` resolve a copy. They never mutate the config passed in.

## Missing values

- A `???` value survives `load_config`.
- A consumer of the `$base` that carries it, or an override, can fill it.
- If it is still missing, accessing it raises OmegaConf's `MissingMandatoryValue`.
  Validating or instantiating any node that contains it raises
  `ConfigValidationError`, caused by `MissingMandatoryValue`. Both name the full
  key.

## Imports

- The syntax is `~import <path>[#<node>]`. Whitespace around `<path>` and around
  `<node>` is ignored.
- A relative path is resolved against the directory of the importing file. An
  absolute path is used as is.
- By default an import may read any file the process can read.
  `load_config(..., import_root=DIR)` rejects an import whose path, after
  interpolations and symbolic links are resolved, is not inside `DIR`. An
  `import_root` that does not exist raises `FileNotFoundError`, and one that is not
  a directory raises `NotADirectoryError`. The root file itself is not checked.
- `<node>` is a dot-separated path from the root of the imported file. A segment
  selects a key in a mapping or an integer index in a list (`#a.b.0`). A negative
  index counts from the end (`#a.b.-1`). An empty `<node>` selects the whole file.
- An import can replace a mapping value or a list item. The imported file may be a
  mapping or a list.
- A file that holds a single value (`hello`, `5`) raises `ConfigValidationError`,
  whether it is the root or imported. A list is allowed in an imported file, but not
  at the root of the file passed to `load_config`. An empty file, and a document that is only
  `null` or `~`, is an empty mapping.
- Cycles are detected per import chain: a file that imports itself, directly or
  through other files, raises `ConfigValidationError`. Importing the same file from
  two branches (a diamond) is not a cycle.
- Every import produces an independent copy. Changing one imported node never
  changes another import of the same file or node.
- Each imported file is read once per `load_config` call.
- A statement with more than one `#` raises `ConfigValidationError`. File names
  containing `#` cannot be imported.
- A `<node>` segment that walks through a scalar, a non-integer segment on a list,
  or an out-of-range index raises the same `ConfigValidationError` as a missing
  node. A path that goes through an interpolation in the imported file raises
  `ConfigValidationError` too; interpolations are not resolved while importing.

## Instantiation

- A mapping with `$class` is instantiable. `$class` is a dotted import path
  `module.attribute`; the attribute is imported and called.
- `instantiate` and `prepare` resolve the node (after `overrides`), then validate it
  as `validate` does ([Validation](#validation)), with the same `allowed_modules`, then build it. A config error therefore raises
  `ConfigValidationError` before any configured target or `from_config` is called. So
  does a resolution error: a `???`, an interpolation that fails, or an exception
  from a resolver, which OmegaConf wraps in `InterpolationResolutionError`.
  OmegaConf's error is the `__cause__`, and the message names the full key.
- If the imported object has a `from_config` attribute, `from_config(arguments)` is
  called instead of the object. This is duck-typed: `Configurable` is one
  implementation, not a requirement. `arguments` is a plain `dict` of the
  materialized arguments, or the typed config when the class has a schema ([Typed configs](#typed-configs)).
- Nested instantiable nodes, in mappings and lists, are built before their parent,
  and the parent receives the built objects.
- A raw `dict` is resolved exactly like a `DictConfig`: `${…}` is resolved, and
  `???` raises `MissingMandatoryValue`. It is converted with `OmegaConf.create`, so
  its values must be types OmegaConf supports. A value such as an arbitrary Python
  object raises `UnsupportedValueType`.
- Errors from a constructor or `from_config`:
  - Any `Exception` raised by the call propagates unchanged, with the same type,
    arguments and traceback.
  - It gets one note, `while instantiating <path> (<class>)`. `<path>` is the
    dotted key path of the failing node from the config passed to `instantiate`,
    with list indices as segments (`items.0.model`), or `<root>` for the top node.
    `<class>` is the `$class` value.
  - A partial from `prepare` or `$partial` is called outside omegakit, so its errors
    get no note.

## References

- A mapping with `$ref` is replaced by the imported object, without calling it.
  `$ref` allows no sibling keys except `$meta`. A top-level `$ref` is not
  instantiable: `instantiate` requires `$class` at the top.

## Partials

- `$partial: true` returns a `functools.partial` of the class (or of its
  `from_config`) with the materialized arguments. Nested objects are still built
  immediately.
- `prepare(config)` is `instantiate` with the top-level call deferred. Nested nodes
  are built during `prepare`, and nested `$partial` nodes stay partials.
- Call-time keyword arguments to a partial from `prepare` or `$partial`:
  - For a class without `from_config`, they reach the constructor, and a call-time
    value wins over a config value of the same name.
  - For a class with `from_config`, they reach `from_config` as `**kwargs`. The
    arguments mapping stays the first positional argument.
  - The default `Configurable.from_config` forwards `**kwargs` to the constructor:
    it calls `cls(**{**fields, **kwargs})`, where `fields` are the typed config's
    fields (shallow) or the arguments mapping. A call-time value replaces a field of
    the same name, as it does for plain classes.
- `$partial: true` makes a node partial, and `$partial: false` does not. Any other
  value, including the string `"true"` and `1`, raises `ConfigValidationError`.

## Metadata

- `$meta` is never passed to a constructor or to `from_config`.

## Reserved keys

- Every key that starts with `$` is reserved for omegakit. The defined keys are
  `$class`, `$ref`, `$partial`, `$meta`, `$base` and `$defaults`.
- `~import` is a value prefix, not a key. Only a string value that starts with
  `~import` is an import. Elsewhere in a string it is literal text.
- `load_config` keeps unknown `$` keys untouched.
- When validating or instantiating, any mapping with a `$` key that is not allowed
  there raises `ConfigValidationError`. A `$class` node allows `$meta` and `$partial`, a `$ref` node allows
  `$meta`, and a plain mapping allows only `$meta`. In particular, `$class` and
  `$ref` cannot be combined.

## Typed configs

A class that subclasses `Configurable[TConfig]` with a dataclass `TConfig` has a
**schema**. Its config is validated and built into a `TConfig` instance, the typed
config, which `from_config` receives. Every other class, including a bare
`Configurable` and a `TypedDict` or `Mapping` `TConfig`, behaves as in [Instantiation](#instantiation).
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
4. **Object and `Any` fields** (children before parent) are built as in [Instantiation](#instantiation). A plain
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
validated before any configured target is built ([Instantiation](#instantiation)), so a config error never
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

1. `load_config` assembles the full config ([Pipeline](#pipeline)). It checks no schema.
2. `validate` checks the assembled config, or any node of it.
3. `instantiate` and `prepare` run the same check on the node they build before
   building it ([Instantiation](#instantiation)).

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
- Reserved keys ([Reserved keys](#reserved-keys)) are checked, and `$meta` is ignored.
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

## Editor schemas

`generate_json_schema(schema)` and the command `omegakit json-schema` ([Command line](#command-line))
generate a JSON Schema (draft-07) for YAML files. The argument is a root schema
dataclass ([Validation](#validation)), or a `Configurable` class whose schema describes a fragment file.

- Every value, scalar or whole node, may also be an interpolation (`${…}`), `???`
  or an `~import`.
- Every mapping accepts any `$` key. Other unknown keys are errors.
- Nothing is required, because values may come from `$base`, `$defaults`, imports or
  overrides. Missing values are caught by `validate` or `instantiate`.
- Enums list their member names, and the string and integer values that are not
  also a name. `Literal` fields list their values.
  Fixed-length tuples give arrays with one schema per position.
- An object field whose class is a `Configurable` with a dataclass schema
  is checked against that schema (`if`/`then`), but only when its `$class` names the
  class's defining module and qualified name. Any other `$class`, such as a
  re-export or a subclass, accepts any mapping.
- Field descriptions are not generated.

## Command line

The `omegakit` command (also `python -m omegakit`) has one subcommand per task. It
puts the working directory on the import path, so `$class`, `--schema` and
`json-schema` import paths resolve from there.

**Arguments.** `check` and `show` take config files and `key=value` overrides in
any order. An argument that names an existing file is a config file, even if it
contains `=`. Otherwise it is an override if it has a `=` with no `/` before it, and
a config file (which then fails to load) if not. Overrides apply to every file.
Their `--import-root DIR` passes `import_root` to `load_config` ([Imports](#imports)).

**Exit codes.** 0 on success, 1 when a config is invalid or cannot be loaded, 2 for
usage errors (a missing config file, an unknown option, an `--schema` or
`json-schema` import path that cannot be imported, an `--import-root` that is not a
directory).

- `omegakit check CONFIG... [KEY=VALUE...] [--schema IMPORT_PATH] [--allow-missing]
  [--allow-module NAME]... [--import-root DIR]`
  loads each file with the overrides and validates it ([Validation](#validation)). Each `--allow-module`
  adds an entry to `allowed_modules` ([Validation](#validation)); without one, every module is allowed. It prints one line per
  failing file, `<file>: <exception type>: <message>`, and nothing for valid files.
  Every exception from loading or validating counts as a failure of that file, and
  so does a `SystemExit` raised by a module that is imported; the other files are
  still checked. `KeyboardInterrupt` stops the command.
- `omegakit show CONFIG [KEY=VALUE...] [--node KEY] [--resolve] [--keep-meta]
  [--show-secrets] [--import-root DIR]`
  prints the assembled config as YAML, or the node at `KEY`. `KEY` is a dotted path
  with the same syntax and walk as `~import file#node` ([Imports](#imports)): `items.0.name`, and
  `items.-1` from the end. The node is printed unresolved: an interpolation prints
  as written, `???` as `???` and `null` as `null`. A path that goes through an
  interpolation, or a node that does not exist, exits with 1. `--resolve` follows
  interpolations on the path, and resolves only the selected node (the whole config
  without `--node`); missing values print as `???`, and any other resolution error
  exits with 1 and one line, like a load error. A scalar node prints as its value.
  Secrets are masked as by `mask_secrets` ([Environment](#environment)), with the secrets of the whole
  config, even with `--node`: by key in every mode, and by environment variable and
  by value with `--resolve`. `--show-secrets` turns masking off.
- `omegakit json-schema IMPORT_PATH [-o FILE] [--check]` prints or writes the JSON
  Schema ([Editor schemas](#editor-schemas)). With `--check`, which needs `-o`, it writes nothing and exits with 1
  if `FILE` is missing or differs from the generated schema (compared as JSON).

## Resolvers

- OmegaConf's own resolvers, such as `oc.env`, are always available:
  `${oc.env:NAME}` reads an environment variable and `${oc.env:NAME,default}` falls
  back to a default. omegakit does not register or change them.
- Resolvers are opt-in. Registration is global to OmegaConf, and an existing name
  raises unless `replace=True` is passed. `omegakit.resolvers` exports nothing:
  each resolver is imported from its own module, which carries its own
  dependencies.
- Resolvers are registered with the API of the installed OmegaConf
  (`register_resolver` on 2.4, `register_new_resolver` on 2.3), so neither warns.

## Errors

`ConfigValidationError` covers every problem in a config's content, including those
that `load_config` finds while loading; the error it wraps, from PyYAML, OmegaConf
or the file system, is its `__cause__`. Only a missing root file passed to
`load_config` raises `FileNotFoundError`.

| Misuse | Exception | Message contains |
|---|---|---|
| Root file passed to `load_config` does not exist | `FileNotFoundError` | the path |
| A file that is not valid YAML, has duplicate keys or unknown tags, or is not UTF-8 | `ConfigValidationError`, caused by PyYAML's error or `UnicodeDecodeError` | `Cannot load`, the file, the line and column |
| A file that holds a single value, not a mapping or a list | `ConfigValidationError` | `single value` and the file |
| A root file passed to `load_config` that holds a list | `ConfigValidationError` | `root is a list` and the file |
| Circular `~import` | `ConfigValidationError` | `Circular import detected`, the statement and the files |
| `~import` of a missing or unreadable file, or of an invalid file | `ConfigValidationError`, caused by the `OSError` or the load error | `Cannot import`, the statement and the importing file |
| `~import` of a missing node | `ConfigValidationError` | `selects node`, the node and the files |
| `~import` selector through a scalar, or a bad or out-of-range list index | `ConfigValidationError` | as missing node |
| `~import` with more than one `#` | `ConfigValidationError` | `more than one` `#` |
| `~import` of a file outside `import_root` | `ConfigValidationError` | `outside the import root`, the statement and both paths |
| `~import` path with an interpolation that fails | `ConfigValidationError`, caused by OmegaConf's error | `Cannot resolve`, the statement and the importing file |
| `$base` not a mapping or list of mappings | `ConfigValidationError` | `$base` |
| `$base` or `$defaults` interpolation to a key that never appears | `ConfigValidationError`, caused by OmegaConf's error | `Cannot resolve` and the full key |
| `$base` or `$defaults` interpolations that refer to each other | `ConfigValidationError` | `references form a cycle` and the nodes |
| `$defaults` not a mapping | `ConfigValidationError` | `$defaults` |
| Overrides of another type than `DictConfig`, `dict` or `list`, including a `ListConfig` | `TypeError` | `Unsupported overrides type` |
| An override that does not parse, has an unsupported value type, or is rejected by a struct config, in `load_config`, `instantiate` or `prepare` | `ConfigValidationError`, caused by PyYAML's or OmegaConf's error | `override`, and the override or its key |
| `instantiate`/`prepare` on a node without `$class` | `ConfigValidationError` | `<root>` and `has no` `$class` |
| `$class`/`$ref` module not found | `ConfigValidationError`, caused by `ModuleNotFoundError` | `Cannot import`, the node path and the module |
| `$class`/`$ref` attribute not found | `ConfigValidationError`, caused by `ImportError` | `Cannot import`, the node path, `Could not import` |
| `$ref` with sibling keys other than `$meta` | `ConfigValidationError` | `cannot contain any other keys` |
| `$class`/`$ref` in a module that `allowed_modules` does not allow ([Validation](#validation)) | `ConfigValidationError` | the path, the node and `allowed_modules` |
| `allowed_modules` given as a string | `TypeError` | `not the string` |
| Raw dict value that OmegaConf does not support | `UnsupportedValueType` | the key |
| Unknown `$` key, or `$class` with `$ref`, at validation or instantiation | `ConfigValidationError` | the key and `reserved` |
| `$partial` not a boolean | `ConfigValidationError` | `$partial` |
| `???` accessed | `MissingMandatoryValue` | the full key |
| Unresolvable `${…}` accessed | `InterpolationKeyError` (or another OmegaConf error) | the key |
| `???`, unresolvable `${…}` or a failing resolver, validated or instantiated | `ConfigValidationError`, caused by OmegaConf's error | `Cannot resolve` and the full key |
| Exception from a constructor or `from_config` | unchanged | original message, plus the note from [Instantiation](#instantiation) |
| Schema outside the supported subset ([Typed configs](#typed-configs)) | `ConfigValidationError` | the field and the fix |
| Schema that does not match `__init__` ([Typed configs](#typed-configs)) | `ConfigValidationError` | the field or parameter |
| Unknown field, missing required field, or invalid native value | `ConfigValidationError` | the node path and the schema |
| Object field whose `$class` is not the annotated class or a subclass, or a `$ref` that is not an instance | `ConfigValidationError` | the field path, the expected class and the given node |
| `make_node()` for a class or function not defined at module level | `ValueError` | `module level` |
| Type variable in a `Configurable` base that cannot be substituted | `TypeError` | `Cannot resolve type variable` |
| Resolver registered twice without `replace=True` | `ValueError` | `already registered` |
| Torch resolver without PyTorch installed | `ImportError` | `require PyTorch` |

A malformed dotlist override such as `["a"]` is not an error: OmegaConf sets `a` to
`None`.

## Environment

- Importing `omegakit` or any of its modules has no side effects: no resolver is
  registered, and `torch` is not imported.
- omegakit does not load `.env` files.
- omegakit supports OmegaConf 2.3 and 2.4 (`omegaconf>=2.3,<2.5`) and behaves the
  same on both. Assembly uses private OmegaConf node APIs, so CI tests the lowest
  supported version, the locked version and the newest pre-release in the range.
- Configs import and call arbitrary Python objects. Load them only from trusted
  sources (see Trust below).

### Trust

Loading, validating, checking and showing a config are not safe on untrusted
input. Validation checks the shape of values; it is not input sanitisation. Code
and I/O happen without anything being built:

- The modules named by `$class` and `$ref` are imported, which runs their
  import-time code, unless `allowed_modules` limits them ([Validation](#validation)). `allowed_modules`
  is not a sandbox.
- Resolvers run, including OmegaConf's `oc.env`, which reads any environment
  variable of the process. `load_config` itself evaluates interpolations in
  `~import` paths and in `$base` and `$defaults` values. An application that does
  not need `oc.env` can call `OmegaConf.clear_resolver("oc.env")` before loading.
- Every `default_factory` of a schema runs during validation ([Validation](#validation)).
- `~import` reads any file the process can read, unless `import_root` is set ([Imports](#imports)).
  `keep_targets=False` does not make loading safe.
- Overrides carry the same trust as the config file: an override can set `$class`,
  `$ref` and interpolations such as `${oc.env:...}`.
- The command line puts the working directory first on `sys.path` ([Command line](#command-line)), so a
  module there can shadow a `$class` target.
- Reading a special file, such as a FIFO, blocks.
- `~import` fan-out can grow exponentially, because every import is a deep copy,
  and a long chain of `$base` references costs time quadratic in its size.
- Any string value that starts with `~import` is an import, so a tool that writes
  YAML from untrusted strings must not let them start with it.
- Error messages, and so CI logs, can contain scalar config values; mappings are
  described by their keys.

Resolved configs and objects built by `instantiate` contain the real values of
secrets read with `${oc.env:...}`. Log `mask_secrets(config)` instead of a resolved
config, and keep secrets out of arguments that components save, such as
hyperparameters written into checkpoints.

### Masking secrets

`mask_secrets(config, *, keys=())` takes an unresolved config, such as the result
of `load_config`, and returns it resolved as plain `dict`s and `list`s for logging,
with secrets replaced by `***`:

1. **By key.** A key is split into words at `_`, `-`, `.` and camelCase
   boundaries. It is secret when its words contain `password`, `passwd`, `pass`,
   `passphrase`, `secret`, `token`, `credential`, `auth`, `bearer`, `cookie`,
   `dsn`, `webhook` or `apikey`, or the sequences `api key`, `private key` or
   `access key`, each also in the plural. Whole words only: `pad_token` is
   secret, `tokenizer` is not. A secret key masks every value below it. `keys`
   adds entries, each a word or a space-separated sequence; the defaults stay.
2. **By environment variable.** A value whose unresolved text reads
   `${oc.env:NAME}`, also with spaces or nested in another interpolation, is
   masked when `NAME` is secret by the same rule: `DB_PASSWORD` is, `APP_ENV` and
   `PWD` are not.
3. **By value.** The resolved strings masked by 1 and 2 that are at least 8
   characters long are replaced by `***` inside every other string, longest first,
   such as a password inside a URL. Numbers and keys are never rewritten.

A masked value is resolved only to collect it for 3; if that fails, it is masked
anyway. A masked value that is not a string becomes the string `***`. A missing
value prints as `???`. Any other resolution error raises `ConfigValidationError`.

Not masked: a secret in a value whose key names no secret, a secret shorter than 8
characters used elsewhere, a secret used as a key, a value read by a resolver other
than `oc.env`, and objects built by `instantiate`. A secret equal to a common word
masks that word in every other string.
