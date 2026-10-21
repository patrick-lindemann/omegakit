# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- A key may be annotated with a union of several `TypedDict`s, also as the item of a
  `list` or `dict`. A mapping is checked against the first member it fits by its keys
  and its `Literal` values, and one that fits none raises `ConfigSchemaError` naming
  every member. A union in a key raised `SchemaDefinitionError`, and a union in a
  `list` or `dict` checked every item against its first member.
- A `TypedDict` behind a type alias with arguments, such as `Optional[ModelConfig]`
  for `Optional = TypeAliasType("Optional", T | None, type_params=(T,))`, or behind
  `Annotated`, is checked. OmegaConf took the mapping as a plain `dict`, so unknown
  keys and wrong values passed, and an `Annotated` alias of a `type` statement raised
  `SchemaDefinitionError`.
- `Required` and `NotRequired` decide whether a key is required also inside
  `Annotated` or `ReadOnly`, as in `Annotated[Required[int], "doc"]`. Under
  `from __future__ import annotations`, and with `typing.TypedDict` on Python 3.10,
  such a key followed the totality of its `TypedDict` instead.
- The items of a container in a union with other members, as in
  `list[ModelConfig] | int` or `list[Model] | Model`, are checked. OmegaConf read the
  first as plain data, which rejected valid lists on Python 3.11 and newer and
  accepted invalid items on Python 3.10, and the items of the second were not checked.
  A mapping that fits no `TypedDict` of a union with a `dict` is checked as the `dict`.
  Two containers of one kind, as in `list[ModelConfig] | list[DataConfig]`, raise
  `SchemaDefinitionError`.
- A `$symbol` that names a `list`, `tuple` or `dict` is checked by the item annotation
  of its field, as in `list[ModelConfig]` or `dict[str, Model]`, and its items are
  converted. Only a `dict` in a field annotated with a `TypedDict` was checked, so
  wrong items passed.
- A class that a `$target` function returns into a `type[X]` field must be a subclass
  of `X`. Any class passed.
- Each member of a union is checked on its own, so `type[Model] | type` takes any
  class. It rejected every class that is no subclass of `Model`.

## [0.11.0] - 2026-10-20

### Added

- omegakit runs on Python 3.10 and 3.11. It required Python 3.12. On Python 3.10, a
  traceback leaves out the notes that omegakit adds to an error, which `__notes__`
  holds as on later versions.
- A schema may be a `typing_extensions.TypedDict`. It raised `SchemaDefinitionError`.
- A field may be annotated with a `typing_extensions.TypeAliasType`, which Python 3.10
  and 3.11 need in place of a `type` statement. OmegaConf checks and converts its value
  as that of a `type` statement, except where a type parameter is a `TypeVarTuple`, a
  `ParamSpec` or has a default. It raised `SchemaDefinitionError`.

### Changed

- omegakit depends on `typing-extensions` 4.14 or newer, for the typing features that
  Python 3.10 and 3.11 lack.

## [0.10.0] - 2026-10-15

### Added

- `resolve_includes`, `merge_bases`, `apply_each`, `apply_overrides` and
  `remove_meta` are public functions for assembling configs created in memory.

## [0.9.0] - 2026-10-15

### Added

- `$args` gives the positional arguments of a `$target` node, as a list next to the
  keyword arguments: `{$target: builtins.int, $args: ["ff"], base: 16}` calls
  `int("ff", base=16)`. It builds targets that take arguments only by position, such
  as `torch.nn.Sequential`. With `$partial: true` the items go into the partial; a
  `$base` or an override replaces the list as a whole. A dataclass binds the items to
  its fields by position and checks each like the value of that key; a class with
  `from_config` rejects `$args`. `make_node(torch.nn.Sequential, layer_a, layer_b)`
  writes its positional arguments to `$args`.
- `is_valid(config, schema)` checks a config like `validate`, also with
  `allow_missing`, but returns `False` instead of raising a `ConfigValidationError`.
- `validate`, `instantiate` and `prepare` take a plain `dict` as well as a config,
  and `validate` also a `list` or a `tuple`. They raised an `AttributeError`.
- A schema may contain itself, directly or through other schemas. It raised
  `SchemaDefinitionError`.
- `omegakit` exports every error class, the `Config` type, `cast_config` and
  `ARGS_KEY`, next to the functions and key names it exported before.
- `omegakit --version` prints the installed version, which is also
  `omegakit.__version__`.
- `${torch.device:name}` gives `torch.device(name)`; `register_torch_device_resolver`
  registers it, and so does `register_torch_resolvers`.
- `omegakit.resolvers.numpy` adds `${numpy.dtype:name}`, which gives
  `numpy.dtype(name)`; `register_numpy_resolvers` or `register_numpy_dtype_resolver`
  registers it. Importing the module without NumPy raises `ImportError`.
- Every `register_*` function of `omegakit.resolvers` takes `use_cache`, which
  OmegaConf uses to cache each result by its arguments. It defaults to `True`;
  results were always cached.
- A NumPy page under Resolvers.

### Changed

- **Breaking:** omegakit requires OmegaConf 2.4, from 2.4.0 up to but not including
  2.5.0. It accepted 2.3 as well.
- **Breaking:** Special keys and options are renamed, without aliases:

  | Old | New |
  | --- | --- |
  | `~import`, `IMPORT_KEY` | `~include`, `INCLUDE_KEY` |
  | `$class`, `CLASS_KEY` | `$target`, `TARGET_KEY` |
  | `$ref`, `REF_KEY` | `$symbol`, `SYMBOL_KEY` |
  | `$defaults`, `DEFAULTS_KEY` | `$each`, `EACH_KEY` |
  | `load_config(import_root=...)` | `load_config(include_root=...)` |
  | `--import-root` of `check` and `show` | `--include-root` |

  An old `$` key is rejected as a reserved key, and an `~import` value stays the
  text it is. An include of a file outside `include_root` raises the new
  `IncludeRootError`.
- **Breaking:** `load_config` no longer takes `keep_targets`, and its arguments may
  be given by position. It raises the error of the step that failed, such as
  `ConfigFileSyntaxError` or `ConfigIncludeError`, instead of `ConfigLoadError`
  itself. Config files load as `OmegaConf.load` gives them: a file that holds a
  single string, such as `hello`, is the mapping `{hello: null}`; a single number,
  a boolean or a list at the root raises `ConfigFileSyntaxError`.
- **Breaking:** `~include file#node` and `omegakit show --node` select the node with
  `OmegaConf.select`. The path also takes `a[0]` and follows interpolations, a node
  that holds `???` counts as missing, and a selected single value arrives resolved.
- **Breaking:** The errors are 18 classes under `OmegaKitBaseException`, which is no
  longer an OmegaConf error; no error is a `TypeError` or a `ValueError` either.
  `ConfigLoadError` is the parent of every error that `load_config` raises,
  `ConfigValidationError` of every error that `validate`, `instantiate` and
  `prepare` raise about the config, and `SchemaDefinitionError` reports a wrong
  schema. `ConfigFileNotFoundError` is still a `FileNotFoundError`,
  `ConfigFilePermissionError` a `PermissionError` and `QualifiedNameNotFoundError`
  an `ImportError`. A reserved `$` key raises `ConfigValidationError` wherever it
  stands.
- **Breaking:** An error names its place in its text, as in ``The value is `???`.
  (at `model.depth`)``, and holds it in `full_key` and `file_path`. The place used
  to be a note, which `str(error)` and logging dropped. A place is a full key such as
  `items[0].model` or `model.$target`, and an error from an included file names the
  include that failed, with notes for the includes that led to it. The messages share
  one style (keys in backticks, "mapping", "Cannot …") and say more about the fix,
  such as the fields of the schema for an unknown key or the files of an include
  cycle.
- **Breaking:** A schema is a `TypedDict`, named after its values, as in
  `ModelConfig`, and only checks: it has no defaults, and a key is required unless it
  is `NotRequired` or its `TypedDict` has `total=False`. A `Configurable` names it in
  the class attribute `schema` instead of a type argument: replace
  `class Model(Configurable[ModelConfig])` with `class Model(Configurable)` and
  `schema = ModelConfig`. `from_config` takes `config: Any` and receives the checked
  values as a `dict` with the keys that the config gives. omegakit no longer depends
  on `typing_extensions`.
- **Breaking:** A dataclass is a class that `$target` builds, never a schema. A field
  annotated with a dataclass holds an object and takes a `$target` or a `$symbol`;
  a mapping without `$target` there raises ``Expected `Data`, but the config gives a
  mapping.`` A field annotated with a `TypedDict` holds a plain `dict`, takes at most
  one `TypedDict` (a union of two raises `SchemaDefinitionError`), and checks a
  `$symbol` to a `dict` like a mapping of the config.
- **Breaking:** OmegaConf checks and converts the data fields of a schema, and its
  rules replace omegakit's own: a `Literal` needs its exact value, a union no longer
  converts the items of a list, a tuple cannot hold `???`, and `Sequence`, `Mapping`
  and `set` raise `SchemaDefinitionError`. The same rules apply to the keys of every
  dictionary and to each position of a tuple, also where the items are objects or
  mappings: the key `FAST` of `models: dict[Mode, Model]` arrives as `Mode.FAST`, and
  `pair: tuple[nn.Module, float]` checks its first item by class. A wrong number of
  tuple items raises `ConfigSchemaError`. A field annotated `type[X]` takes only a
  subclass of `X`.
- **Breaking:** The second argument of `instantiate` and `prepare`, given by position
  or as `schema=` (it could be given only as `schema=`), is the class of the result,
  and what was built is checked against it with `isinstance`, as is the result of a
  function that `$target` names in a field annotated with a class. A schema is
  accepted only by `validate`. Only a mapping with `$target` is instantiated, and
  `prepare` raises `ConfigSchemaError` for a root whose `$target` is a function.
- **Breaking:** A node with `$partial: true`, and the root of `prepare`, may leave
  required keys of its schema open, to be given as keyword arguments when the
  partial is called. Such an argument replaces the value of the config in the `dict`
  that `from_config` receives; a required key that is still open raises
  `ConfigSchemaError` at the call.
- **Breaking:** `validate`, `instantiate` and `prepare` no longer take
  `allowed_modules`, and `omegakit check` no longer has `--allow-module`: nothing
  limits the modules that `$target` and `$symbol` import. `instantiate` and `prepare`
  no longer take `overrides`; apply them with the `overrides` of `load_config`, or
  with `OmegaConf.merge` for a config in memory.
- **Breaking:** `walk(node, order="pre-order")` yields every node, value nodes, lists
  and tuples included, and with `order="post-order"` the children before their
  parent. `walk(config)` yielded only the mappings, parents first.
- **Breaking:** `${secret:...}` wraps the interpolation that gives the secret, such
  as `${secret:${oc.env:TOKEN}}`; replace every `${secret:NAME}` with
  `${secret:${oc.env:NAME}}`. `omegakit show --resolve` prints `${secret:...}` and
  every value built from it as `***`, without reading the secret.
- **Breaking:** The torch resolvers are `${torch.dtype:...}` and `${torch.has_cuda:}`,
  and `register_cuda_available_resolver` is `register_torch_cuda_resolver`: replace
  `${dtype:bfloat16}` with `${torch.dtype:bfloat16}` and `${cuda_available:}` with
  `${torch.has_cuda:}`. `register_torch_resolvers` registers its resolvers one after
  the other, so a taken name raises after the ones before it are registered; with
  `replace=False` it registered none if a name was taken.
- **Breaking:** Importing `omegakit.resolvers.torch` without PyTorch raises
  `ImportError`. It was raised when a resolver was registered.
- **Breaking:** `omegakit check` and `omegakit show` take overrides as
  `--overrides KEY=VALUE ...`, and every other argument is a config file: replace
  `omegakit show app.yaml seed=3` with `omegakit show app.yaml --overrides seed=3`.
  `check` exits with 2 for a `--schema` that is not a class, before it reads a file;
  it reported the error for each file and exited with 1. `show --resolve` reports an
  interpolation to a missing or unknown key as an error instead of printing `???`;
  with the new `--allow-missing` it prints `???` as before, and so does `--node` for
  a node that holds `???`.
- **Breaking:** A `$base` is merged after the `$base` of every node that encloses
  it, so a `${…}` base sees an enclosing node with the keys that the enclosing
  `$base` brings in. `data.test: {$base: ${..train}}` gets the `train` keys that a
  `$base` of `data` adds, and finds `train` also where only that base brings it; it
  got `train` as written, and raised `Cannot resolve` where only that base brought
  it. Precedence is unchanged: the enclosing base, then the own `$base`, then the
  own keys. A `$base` that names a node inside its own node, where that node holds
  a `$base`, raises ``The `$base` of these nodes wait for each other``; it was
  merged with that node's `$base` merged first.
- `validate` takes `schema` as its second argument by position as well. It took it
  only by keyword.
- The API and Changelog pages of the documentation moved to `reference/api/` and
  `reference/changelog/`.
- The Imports page of the Guide is now Includes, at `guide/includes/`.
- Dataclass schemas is now TypedDict schemas, at `schemas/typed-dict-schemas/`.

### Removed

- **Breaking:** `generate_json_schema`, the `omegakit export-schema` command and the
  Editor support page, as OmegaConf generates no JSON Schema.
- **Breaking:** `check_schema`. A schema that does not fit its class's constructor
  fails when the object is built, with a note that names the node.
- The Restricting imports page, since nothing restricts imports; `include_root` is
  on the Includes page.

### Fixed

- An override that is no `key=value`, whose value is an include, or that is not a
  string raises `ConfigOverrideError`. `seed` set `seed` to `None`, `=5` created the
  key `''`, `layers[0]=1` replaced the list with a mapping, and an include stayed
  text. An override that cannot be applied is named in the message.
- `omegakit check` and `omegakit show` print failures to stderr, with their notes.
  They printed only the first line, to stdout.
- A `$symbol` or `$target` may name a submodule that is not imported yet, such as
  `concurrent.futures`, and an error that a module raises on import gets a note that
  names the node.
- `make_node` raises `ConfigTargetError` for a callable without a name, such as a
  `functools.partial`. It raised an `AttributeError`.
- A schema annotation that fails to evaluate, or a key annotation that OmegaConf does
  not support, raises `SchemaDefinitionError` instead of a `TypeError`, a
  `SyntaxError` or an `AttributeError`. A bare `tuple` field holds a `tuple`, not a
  `list`, and `$meta` in the mapping of a data field is ignored.
- An `OSError` while a config file is read passes through. It was reported as
  `ConfigFileSyntaxError`.
- An included text that ends up as a backslash before `${`, such as `\\${x}`, stays
  that text.
- The error for a cycle of `$base` or `$each` references names only the nodes on the
  cycle.
- `${paths:name}` raises for a name that was not registered. It resolved to `None`.

## [0.8.0] - 2026-09-28

### Added

- A Metadata page in the Guide, for `$meta`.

### Changed

- **Breaking:** The `omegakit json-schema` command is now `omegakit export-schema`,
  with the same arguments.
- The Configs section of the documentation is now the Guide, and its pages moved
  from `configs/<page>/` to `guide/<page>/`, such as `guide/loading/`.
- Each Guide page has its own small example, which shows that page's feature only.
  Every other feature page has a small example of its own too, and each page shows
  its script's complete output.
- Shared defaults is now Defaults, at `guide/defaults/`, and Building objects comes
  before Schemas.
- The command line has its own section, with an overview and a page per command,
  each with examples. The options are left to `--help`. The pre-commit hook moved
  to Checking experiments in CI.
- Handling errors is part of the Guide, at `guide/errors/`.
- The comparison page no longer has a section on OmegaConf itself.
- The documentation and the README use a small PyTorch project as their example,
  instead of `curvefit`: an MLP fitted to noisy samples of a sine wave, with
  `torch.optim` and `torch.nn` named straight from the configs.

### Removed

- The Using with PyTorch recipe, and the Reproducible runs page. Its rules on saving
  a config are on Loading.

### Fixed

- A dataclass schema that OmegaConf cannot validate, such as one with a
  `dict[Path, int]` field, raises `SchemaDefinitionError` from `validate`,
  `instantiate` and `prepare`, as it does from `check_schema`, instead of
  `ConfigValidationError`.

## [0.7.0] - 2026-09-27

### Added

- `${secret:NAME}` reads an environment variable, as `oc.env` does, and
  `omegakit show --resolve` prints each value it gave as `***`, also inside longer
  strings. Register it with `omegakit.resolvers.secrets.register_secret_resolver()`;
  the `omegakit` command registers it itself.
- A Reproducible runs page: seeding, one directory per run, saving the config and
  the overrides, and what omegakit does not do.
- A Dataclass schemas page: a plain dataclass as the schema of a config, its field
  kinds and how a node is checked.
- A Secrets page, which replaces the secret masking part of the Security page.
- Three recipes: Parameter sweeps, Using with PyTorch, and Checking experiments in
  CI.
- `OmegaKitBaseException`, the base of omegakit's errors, and a Handling errors
  page: one handler for config errors, errors when a config is read, and errors
  from constructors.

### Changed

- **Breaking:** `instantiate` and `prepare` take the class of the result as the
  keyword-only `schema=` instead of the positional `expected`. Write
  `instantiate(config, schema=App)` for `instantiate(config, App)`. `schema` is now
  checked: a root with `$class` must name `schema` or a subclass, and a root without
  `$class` is built as `schema`, so a plain root dataclass gives a typed result.
- **Breaking:** `load_config` raises the new `ConfigLoadError` for an invalid file,
  `~import`, `$base` or `$defaults`, and every function raises it for an invalid
  override. Replace `except ConfigValidationError` there with
  `except ConfigLoadError` or `except OmegaKitBaseException`. `except ValueError`
  still catches it.
- **Breaking:** A class that cannot serve as a schema raises the new
  `SchemaDefinitionError` instead of `ConfigValidationError`, from `check_schema`,
  `generate_json_schema`, and from `validate`, `instantiate` and `prepare` for a
  `$class` that names it. A type variable that cannot be resolved raises it instead
  of `TypeError`. `except ValueError` still catches it.
- `ConfigValidationError` is now an `OmegaKitBaseException` and an
  `omegaconf.ValidationError`, so `except omegaconf.ValidationError`,
  `except OmegaConfBaseException` and `contextlib.suppress(OmegaConfBaseException)`
  now also catch it. It is still a `ValueError`.
- The documentation presents omegakit for reproducible experiments. Every example
  uses `curvefit`, a small curve-fitting experiment in plain Python, instead of the
  `webapp` example.
- The documentation is reorganised, and page URLs changed:
  - Command line is in the top group, at `command-line/`.
  - Configs: `guide/loading/` is now `configs/loading/`, and so on. Base is now
    Inheritance, Defaults is Shared defaults, and Interpolation and missing values
    is split into Interpolation, Environment variables and Missing values.
  - Schemas is a section: Dataclass schemas, Validation at `schemas/validation/`,
    and Editor schemas, now Editor support, at `schemas/editor-support/`.
  - Building objects: Building objects is now Instantiation, and Typed configs is
    now Configurable classes, which covers only what a class adds.
  - Resolvers have their own section, with an overview and a page per module.
  - Security is three pages: Trust model at `security/trust-model/`, Restricting
    imports and Secrets.
  - Swapping is now Swapping implementations, at
    `recipes/swapping-implementations/`.
- The Rules section of each feature page names the errors of its feature.
- The comparison page compares omegakit with experiment config tools: Hydra and
  hydra-zen, jsonargparse and LightningCLI, Fiddle, gin-config, ml_collections,
  Sacred and OmegaConf. It no longer compares pydantic-settings and Dynaconf.
- The README shows an experiment with a shared base and a root dataclass.

### Removed

- **Breaking:** `mask_secrets`, and the guessing of secrets by key and variable
  names in `omegakit show`. Save and log the config from `load_config` unresolved:
  it holds `${secret:NAME}`, not the value. `--show-secrets` now only turns off the
  masking of `${secret:...}` values.
- The `webapp` example, the Errors page, and the Manifests and Per-tenant configs
  recipes. Shared defaults covers what Manifests showed.

### Fixed

- A plain dataclass named by `$class` is checked and built as its own schema.
  `validate` now rejects unknown keys and values of the wrong type in it, and
  `instantiate` converts its values, so `epochs: "4"` gives the integer 4.

## [0.6.1] - 2026-09-27

### Fixed

- The 0.6.0 changelog entry described the documentation before its restructuring.

## [0.6.0] - 2026-09-27

### Added

- `load_config(..., import_root=DIR)` rejects any `~import` that reads a file
  outside `DIR`, after interpolations and symbolic links are resolved. The default
  still allows any file.
- `omegakit check` and `omegakit show` take `--import-root DIR`.
- `validate`, `instantiate` and `prepare` take `allowed_modules`, which limits the
  modules that `$class` and `$ref` may name. A module that is not allowed is never
  imported, and an object is also checked against the module it is defined in. It is
  not a sandbox: allowing `builtins`, `os`, `subprocess`, `importlib`, `shutil` or
  `pickle` equals no restriction.
- `omegakit check --allow-module NAME`, repeatable, passes `allowed_modules` to
  `validate`.
- `mask_secrets(config, *, keys=())` resolves a loaded config for logging with
  secrets replaced by `***`: by key name (`password`, `token`, `api_key`, ...), by
  secret-named `${oc.env:...}` variables, and by value inside other strings, such as
  a password in a URL.
- A Security page: what loading, validating, checking and showing run and read,
  the `allowed_modules` and `import_root` limits, CI advice, and how to log a config
  without its secrets.
- A page that compares omegakit with Hydra, OmegaConf, jsonargparse and
  LightningCLI, pydantic-settings and Dynaconf.

### Changed

- **Breaking:** `instantiate` and `prepare` raise `ConfigValidationError` for a
  `???`, an interpolation that cannot be resolved and an exception from a resolver,
  with OmegaConf's error as `__cause__` and the full key in the message. Callers
  catching `MissingMandatoryValue` or `InterpolationKeyError` from them must catch
  `ConfigValidationError`. `MissingMandatoryValue` was not a `ValueError`, so
  `except ValueError` now also catches a missing value.
- **Breaking:** `instantiate`/`prepare` on a node without `$class` raise
  `ConfigValidationError` instead of `ValueError` (still a `ValueError` subclass),
  and the message no longer prints the whole config.
- **Breaking:** `load_config` raises `ConfigValidationError` for every problem in a
  config file's content: YAML syntax errors, duplicate keys, unknown tags, non-UTF-8
  files, circular or malformed imports, a missing or unreadable imported file,
  interpolation errors in `~import` paths and in `$base`/`$defaults`, and invalid
  `$base`/`$defaults` values. The original error is `__cause__`, and import errors
  name the statement and the importing file. Only a missing root file still raises
  `FileNotFoundError`.
- **Breaking:** An override that does not parse (`a=[1`, `a=${`), has a value of an
  unsupported type, or is rejected by a struct config raises `ConfigValidationError`
  from `load_config`, `instantiate` and `prepare`, naming the override or its key.
- **Breaking:** Overrides of an unsupported type, including a `ListConfig`, raise
  `TypeError` instead of `ValueError`; a `ListConfig` used to fail inside
  OmegaConf's merge.
- **Breaking:** A config file that holds a single value is rejected with
  `ConfigValidationError`, as the root and as an import. `hello` used to load as
  `{hello: None}`, `"a: 1"` as `{a: 1}`, and `5` raised an `OSError`. Empty files
  and `null`/`~` documents stay empty mappings.
- **Breaking:** `load_config` rejects a file whose root is a list with
  `ConfigValidationError`, so its return type `DictConfig` holds. Imported files may
  still be lists.
- **Breaking:** `omegakit show --node` no longer resolves the selected node: an
  interpolation prints as written, so `--node db.url` does not print a secret from
  `${oc.env:...}`. `--resolve` resolves only the selected node. The path uses dots
  only, like `~import file#node` (`items.0`, `items.-1`); bracket syntax is gone. A
  path through an interpolation needs `--resolve`, `null` prints `null`, and an
  absent node is an error.
- **Breaking:** `omegakit show` masks secrets as `***`: by key name in every mode,
  and by secret environment variable and by value with `--resolve`, using the whole
  config even with `--node`. `--show-secrets` turns masking off.
- `validate` no longer constructs the schema's nested dataclasses, so their
  `__post_init__` runs once, while building, and not during validation. The
  `validate` docstring and the Validation guide list the code that still runs during
  validation: module imports, resolvers, `__instancecheck__`/`__subclasscheck__` and
  `default_factory`.
- Only a missing `$class`/`$ref` module (or parent package) and a missing attribute
  raise `ConfigValidationError`. An `ImportError` raised by the named module itself,
  such as a missing dependency, propagates with its own type.
- The documentation names `ConfigValidationError`, which the code already raised, for
  reserved `$` keys, a non-boolean `$partial` and a `$ref` with siblings.
- Whitespace before `#` in an `~import` path is ignored: `~import lib.yaml #a`
  imports `lib.yaml`, not `lib.yaml `.
- Errors for an invalid `$base` or `$defaults` name the node path (`outer.inner`,
  `<root>`) instead of printing the whole node.
- Validation errors describe a mapping by its keys and a list by its length instead
  of printing their values. Scalar values are still printed.
- Releases publish only a commit on `main` that passes CI, from actions pinned to
  commit SHAs, and upload PEP 740 attestations.
- The documentation is rebuilt around one example application, `webapp`, with a new
  Getting started, a guide page per feature and three recipes. The exact rules of
  each feature are in a Rules section on its guide page, and the Contracts section
  is gone. Page URLs changed, for example `guide/loading.html` is now
  `guide/loading/`, and old URLs do not redirect.

### Removed

- `is_valid`. Use `validate` and catch the error: `try: validate(config) except
  ConfigValidationError: ...`.

### Fixed

- Optional `list`, `dict` and dataclass fields (`list[int] | None`, ...) are
  validated: `xs: abc` no longer becomes `["a", "b", "c"]`, and wrong values raise
  `ConfigValidationError` instead of a raw `TypeError` or `AttributeError`.
- A fixed-length tuple field rejects a list with too many items; `[1, 2, 3]` for
  `tuple[int, int]` was silently truncated to `(1, 2)`.
- A union without `None`, such as `Sub | int`, rejects `null`.
- A union with a container member, such as `int | list[int]`, rejects scalars of
  other types (`"wrong"`, `3.5`, `True`) and `null`.
- `allow_missing=True` also accepts `???` inside fixed-length tuples and in the
  dataclass member of a union.
- A dataclass default from `default_factory` is used as built, at every nesting
  depth; it was rebuilt from its fields, so its `__post_init__` ran twice on the
  same values.
- A `$class` or `$ref` that is not a string (a number, `null`, a list) raises
  `ConfigValidationError` naming the node, instead of an `AttributeError`.
- `validate` rejects a `$class` target that is neither callable nor has
  `from_config`, such as `$class: math.pi`, which only failed while building. `$ref`
  still accepts any object.
- A malformed import path (`nodots`, `.Foo`, `..mod.X`) in `$class`, `$ref` or
  `check --schema` is reported as not an import path, instead of `Empty module name`
  or a raw `TypeError`.
- Reserved keys and nested `$class`/`$ref` nodes under `Callable` and `Protocol`
  object fields are validated; they were only caught, with a raw `ValueError` or
  `ModuleNotFoundError`, while building.
- `check_schema` rejects a field that names a positional-only `__init__` parameter,
  even when `__init__` takes `**kwargs`; building such a class failed with a raw
  `TypeError`.
- `check_schema` skips only the constructor parameters whose annotations do not
  resolve, such as types imported under `TYPE_CHECKING`, and checks the rest; one
  unresolvable annotation used to switch the assignability check off for every
  parameter.
- A schema annotation that does not resolve is blamed on the right field when the
  schema inherits fields from a dataclass in another module.
- `generate_json_schema` raises its documented `TypeError` for an object that is not
  a class, instead of `issubclass() arg 1 must be a class`.
- A dataclass schema that contains itself, directly or through other dataclasses,
  raises `ConfigValidationError` naming the cycle, instead of `RecursionError`.
- `omegakit check` counts a file as invalid when a module it imports calls
  `sys.exit()`, and checks the remaining files; the command used to stop and exit
  with that status, so `sys.exit(0)` made the check pass.
- `omegakit show --node` on a `null` value printed that the node does not exist.
- `omegakit show --resolve` reports a resolution error, such as an unknown resolver,
  as one line with exit code 1 instead of a traceback.
- `omegakit json-schema` reports an import path that cannot be imported as a usage
  error (exit code 2) instead of a traceback.

## [0.5.0] - 2026-09-26

### Added

- `omegakit check CONFIG... [KEY=VALUE...] [--schema IMPORT_PATH] [--allow-missing]`
  validates config files without building anything, for terminals, pre-commit
  hooks and CI.
- `omegakit show CONFIG [KEY=VALUE...] [--node KEY] [--resolve] [--keep-meta]`
  prints a config as it is assembled.
- `omegakit json-schema ... -o FILE --check` fails when a committed schema is out of
  date.
- `validate(..., allow_missing=True)` and `is_valid(..., allow_missing=True)` accept
  missing values, for library files and fragments.
- `validate(..., schema=...)` accepts any class: a `Configurable` checks a root that
  builds it, or a fragment without `$class` against its schema.
- Schemas support enums by value, unions with dataclasses, lists and dicts,
  `tuple[int, ...]` and fixed-length tuples, `Sequence` and `Mapping`, `TypedDict`
  fields, `init=False` fields (not configurable), `InitVar` fields with a default,
  keyword-only dataclasses, and `list`/`dict` object fields such as
  `list[Encoder]`. The behaviour is the same on OmegaConf 2.3 and 2.4.
- A plain mapping in a schema field typed as a dataclass with object fields is
  built as that dataclass.

### Changed

- `instantiate` and `prepare` validate the node before building anything. Config
  errors raise `ConfigValidationError` before any constructor runs.
- A `$class` or `$ref` that cannot be imported raises `ConfigValidationError`
  (caused by the `ImportError`) instead of `ImportError`.
- An object field's `$class` must be the annotated class or a subclass; the type of
  the built object is no longer checked after building.
- Scalars in unions must match a member's type exactly.
- OmegaConf 2.4 is supported: `omegaconf>=2.3,<2.5`. Resolvers register through
  OmegaConf 2.4's `register_resolver` when available, without deprecation warnings.

### Fixed

- `$base` and `$defaults` interpolations to a node later in the file that has its
  own `$base` or `$defaults` now see it merged. References that form a cycle raise
  `ValueError` instead of leaving literal keys.

## [0.4.0] - 2026-09-26

### Added

- A documentation site at https://omegakit.readthedocs.io, with a getting-started
  page, a guide page with a runnable example for every feature, a cookbook of
  common patterns and the changelog.

### Changed

- The `Configurable` docstring now reads "A class with a typed config schema and a
  `from_config` hook."

## [0.3.0] - 2026-09-26

### Added

- `validate(config, *, schema=None)` checks a loaded config without building
  anything: every `$class` node against the schema of its class, bottom-up, and
  the root against an optional root schema dataclass. `is_valid` returns the result
  as a boolean.
- `generate_json_schema(schema)` and the command
  `omegakit json-schema <import path> -o <file>` generate JSON Schemas for YAML
  editors from root schemas and `Configurable` classes.
- `Literal` fields of strings, integers or booleans in schemas, also inside lists,
  dicts, optional fields and nested dataclasses.

### Changed

- `node` is renamed to `make_node`.
- A schema validation error names the full key of the invalid value, such as
  `model.encoder.width`, not only the node.

## [0.2.0] - 2026-09-24

### Added

- Typed configs: a `Configurable[TConfig]` subclass with a dataclass `TConfig` has a
  schema. Its config is validated before building (unknown keys, wrong types,
  missing values, with the node path and the schema name), native values are
  coerced by OmegaConf, and `from_config` receives a `TConfig` instance with object
  fields built and `isinstance`-checked. See the typed-configs guide and section 10
  of the configuration contracts.
- `check_schema(cls)` checks that a schema matches `__init__`. It also runs
  automatically, before a node's children are built, for classes that use the
  default `from_config`.
- `node(target, **kwargs)` creates a `$class` node for code-chosen children inside
  `from_config`.
- `ConfigValidationError`, a `ValueError`, for schema and validation errors.

### Changed

- `Configurable`'s `TConfig` defaults to `Mapping[str, Any]` instead of
  `DictConfig`, and `from_config` is typed as
  `from_config(cls, config: TConfig, **kwargs: Any) -> Self`. Overrides must accept
  `**kwargs`.
- The default `Configurable.from_config` passes the fields of a dataclass config to
  the constructor. Mapping configs behave as before.

## [0.1.0] - 2026-09-23

First release. The configuration language is specified in the
[configuration contracts](https://github.com/patrick-lindemann/omegakit/blob/v0.1.0/docs/contracts.md).

### Changed compared with the pre-release version

- A raw `dict` passed to `instantiate` or `prepare` is resolved like a `DictConfig`:
  `${…}` is resolved, `???` raises `MissingMandatoryValue`, and values OmegaConf
  does not support raise `UnsupportedValueType`.
- An exception raised by a constructor or `from_config` keeps its type and gets a
  note naming the failing node, such as `while instantiating model.encoder
  (myapp.Encoder)`. Exceptions are no longer rebuilt, which crashed for exception
  types whose constructors need several arguments.
- Each imported file is read once per `load_config` call.
- An `~import` with more than one `#` raises `ValueError`. Previously everything
  after the second `#` was ignored.
- An `~import` selector that walks through a scalar, or uses a non-integer or
  out-of-range list index, raises the missing-node `ValueError`.
- `$partial` accepts only `true` and `false`; any other value raises `ValueError`.
- `Configurable.from_config` forwards call-time arguments from `prepare` and
  `$partial` to the constructor, and they win over config arguments.
- When instantiating, a `$` key that is not allowed in its node, such as `$foo` or
  `$ref` next to `$class`, raises `ValueError`. Every `$` key is reserved.
- `instantiate(config, expected, *, overrides=None)` and the same for `prepare`:
  the `type` argument is renamed to `expected`, `overrides` is keyword-only, and
  overloads type the result as `expected`, or `Any` without it.
- `omegakit.resolvers` exports nothing; import each resolver from its own module,
  such as `omegakit.resolvers.paths`.
- Python 3.12 is supported.

[Unreleased]: https://github.com/patrick-lindemann/omegakit/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.11.0
[0.10.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.10.0
[0.9.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.9.0
[0.8.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.8.0
[0.7.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.7.0
[0.6.1]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.6.1
[0.6.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.6.0
[0.5.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.5.0
[0.4.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.4.0
[0.3.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.3.0
[0.2.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.2.0
[0.1.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.1.0
