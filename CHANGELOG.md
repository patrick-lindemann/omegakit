# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `validate`, `instantiate` and `prepare` take a plain `dict` as well as a config,
  and `validate` also a `list` or a `tuple`. They raised an `AttributeError`.
- `omegakit --version` prints the installed version, which is also
  `omegakit.__version__`.
- `$args` gives the positional arguments of a `$target` node, as a list next to the
  keyword arguments: `{$target: builtins.int, $args: ["ff"], base: 16}` calls
  `int("ff", base=16)`. It builds targets that take arguments only by position, such
  as `torch.nn.Sequential` and `math.sqrt`. With `$partial: true` the items go into
  the partial. A `$base` or an override replaces the list as a whole. A class with
  `from_config` takes its arguments by name and rejects it. A dataclass binds the
  items to its fields by position, as its constructor does: each is converted and
  checked like the value of that key, a field that is also given by name raises
  `ConfigSchemaError`, and more items than positions raise `ConfigSchemaError`.
- `make_node` takes positional arguments and writes them to `$args`, as in
  `make_node(torch.nn.Sequential, layer_a, layer_b)`.
- `omegakit` exports every error class, such as `ConfigSchemaError` and
  `ConfigIncludeError`, the `Config` type and `ARGS_KEY`, next to `load_config`,
  `validate`, `instantiate`, `prepare`, `make_node`, `Configurable`, `walk` and the
  other key names.
- A schema may contain itself, directly or through other schemas. It raised
  `SchemaDefinitionError`.

### Changed

- **Breaking:** omegakit requires OmegaConf 2.4.0, and no other version. Until
  2.4.0 is released, only its release candidate exists; uv installs it with
  `uv add omegakit --prerelease=allow`.
- **Breaking:** `~import` is now `~include`, and `IMPORT_KEY` is `INCLUDE_PREFIX`.
  Replace `~import base.yaml` with `~include base.yaml`. The old spelling has no
  alias: an `~import` value stays the text it is.
- **Breaking:** `$class` is now `$target`, and `CLASS_KEY` is `TARGET_KEY`. Replace
  `$class: torch.nn.Linear` with `$target: torch.nn.Linear`. The old spelling has no
  alias: a `$class` key is rejected as a reserved key.
- **Breaking:** `$ref` is now `$symbol`, and `REF_KEY` is `SYMBOL_KEY`. Replace
  `$ref: math.sqrt` with `$symbol: math.sqrt`. The old spelling has no alias: a
  `$ref` key is rejected as a reserved key.
- **Breaking:** `$defaults` is now `$each`, and `DEFAULTS_KEY` is `EACH_KEY`.
  Replace `$defaults: {n: 256}` with `$each: {n: 256}`. The old spelling has no
  alias: a `$defaults` key is rejected as a reserved key.
- **Breaking:** `load_config(import_root=...)` is now `include_root`. An include of
  a file outside it raises the new `IncludeRootError`.
- **Breaking:** `load_config` no longer takes `keep_targets`, and its arguments may
  be given by position. It raises the error of the step that failed, such as
  `ConfigFileSyntaxError` or `ConfigIncludeError`, instead of raising
  `ConfigLoadError` itself, and `ConfigFileSyntaxError` for a file whose root is a
  list.
- **Breaking:** omegakit has 18 error classes. `ConfigLoadError` is the parent of
  every error that `load_config` raises: `ConfigFileNotFoundError`,
  `ConfigFilePermissionError`, `ConfigFileSyntaxError`, `ConfigIncludeError` with
  `IncludeRootError`, `ConfigMergeError` for `$base` and `$each`, and
  `ConfigOverrideError`. `ConfigValidationError` is the parent of every error that
  `validate`, `instantiate` and `prepare` raise about the config:
  `ValidationMissingValueError` for a `???`, `ValidationInterpolationError`,
  `QualifiedNameSyntaxError`, `QualifiedNameNotFoundError`, `ConfigTargetError`,
  `ConfigSymbolError` and `ConfigSchemaError`. `SchemaDefinitionError` belongs to
  neither, since it reports a wrong schema.
- **Breaking:** An error names its place in its text, as in ``The value is `???`.
  (at `model.depth`)``, and holds it in `full_key` and `file_path`. The place used
  to be a note, which `str(error)` and logging dropped. An error from an included
  file names the include that failed, and notes name the includes that led to it.
- **Breaking:** `OmegaKitBaseException` is no longer an `OmegaConfBaseException`,
  and no error is an OmegaConf error, a `TypeError` or a `ValueError`. Catch
  `OmegaKitBaseException` or one of its classes instead. `ConfigFileNotFoundError`
  is still a `FileNotFoundError`, `ConfigFilePermissionError` a `PermissionError`
  and `QualifiedNameNotFoundError` an `ImportError`.
- **Breaking:** `omegakit check --import-root` is now `--include-root`, and
  `--allow-missing` and `--allow-module` are gone, as `validate` no longer takes
  `allow_missing` and `allowed_modules`.
- **Breaking:** `omegakit show --import-root` is now `--include-root`.
  `show --resolve` reports an interpolation to a missing or unknown key as an error
  instead of printing `???`. A plain `???` still prints as `???`.
- **Breaking:** `~include file#node` and `omegakit show --node` select the node with
  `OmegaConf.select`. The path also takes `a[0]`, and it follows interpolations
  instead of rejecting a path through one. A node that holds `???` counts as
  missing. A selected single value arrives resolved: an include resolves it in the
  included file, and `show` prints it resolved, with `${secret:...}` as `***`.
- **Breaking:** Config files load as `OmegaConf.load` gives them. A file that holds
  a single string, such as `hello`, is the mapping `{hello: null}` instead of an
  error; a single number or boolean still raises `ConfigLoadError`, now with
  OmegaConf's message.
- **Breaking:** OmegaConf checks and converts the data fields of a schema, and its
  rules replace omegakit's own. A data field accepts what OmegaConf accepts: a
  `Literal` needs its exact value (`"2"` is no longer `2`), a union no longer
  converts the items of a list (`["1", 2]` for `list[int] | int`), a tuple cannot
  hold `???`, and `Sequence`, `Mapping` and `set` raise `SchemaDefinitionError`.
  A wrong value gives OmegaConf's reason, such as `` `hidden` does not match
  `MLPConfig`: Value 'wide' of type 'str' could not be converted to Integer``.
- **Breaking:** A schema is a `TypedDict`, named after its values, as in
  `ModelConfig`. `Configurable.schema` takes nothing else, and a dataclass there
  raises `SchemaDefinitionError`. A schema only checks and has no defaults: a key is
  required unless it is `NotRequired` or its `TypedDict` is declared with
  `total=False`, and the defaults live in the constructor or in the config.
  `from_config` receives the checked values as a `dict` with the keys that the
  config gives, no longer an instance of the schema. A field that is annotated with
  a `TypedDict` holds a mapping without `$target`, which stays a `dict`, and a
  `$target` that names a `TypedDict` raises `ConfigSchemaError`.
- **Breaking:** A dataclass is a class that `$target` builds, never a schema. A
  field that is annotated with a dataclass holds an object, so it takes a `$target`
  or a `$symbol`. A mapping without `$target` raises ``Expected `Data`, but the
  config gives a mapping.`` there, also as an item of a list or a dictionary and
  for `validate(config, Data)`. It used to be built as the dataclass.
- **Breaking:** The second argument of `instantiate` and `prepare` is the class of
  the result, and `instantiate` checks what was built against it with `isinstance`:
  a target that returns something else raises `ConfigSchemaError`. A schema is
  accepted only by `validate`. Only a mapping with `$target` is instantiated: a root
  without one raises, with a class as in ``Expected `Training`, but the config gives
  a mapping.``, and so does a root that is a `$symbol`.
- **Breaking:** A node with `$partial: true`, and the root of `prepare`, may leave
  required keys of its schema open. They are given when the partial is called: an
  argument of the call that is a key of the schema goes into the `dict` that
  `from_config` receives, as written, and replaces a value of the config. Every
  other argument still arrives as `**kwargs`. A required key that is still open
  raises `ConfigSchemaError` at the call. Such a partial wraps a function of
  omegakit instead of `from_config` and takes keyword arguments only.
- **Breaking:** A field takes at most one `TypedDict`: a union of two, such as
  `section: OptimizerConfig | SchedulerConfig`, raises `SchemaDefinitionError`.
- **Breaking:** The result of a function that `$target` names is checked with
  `isinstance` when the function returns, in a field that is annotated with a
  class. It used to pass unchecked. `prepare(config, Class)` raises
  `ConfigSchemaError` for a root whose `$target` is a function, since the result of a
  partial cannot be checked.
- **Breaking:** A tuple may hold objects and mappings, and every position follows
  its annotation: in `pair: tuple[nn.Module, float]` the first item is checked by
  its class and the second is converted, and the items of
  `phases: tuple[OptimizerConfig, ...]` are checked against the `TypedDict`. A
  tuple that is annotated with a class raised `SchemaDefinitionError`, and a mapping
  in a tuple of schemas was not checked. A wrong number of items raises
  `ConfigSchemaError`, as in ``Expected 2 items, but the config gives 1.``
- **Breaking:** The keys of every dictionary follow its key annotation, also where
  the items are mappings or objects: the key `1` raises `ConfigSchemaError` in
  `models: dict[str, Model]`. A field that is annotated `type[X]` takes a subclass
  of `X` and no other class. A `$symbol` to a `dict` in a field that is annotated
  with a `TypedDict` is checked against it like a mapping of the config, and the
  field holds a checked copy. It raised `ConfigSchemaError`.
- **Breaking:** A `Configurable` names its schema in the class attribute `schema`
  instead of a type argument: replace `class Model(Configurable[ModelConfig])` with
  `class Model(Configurable)` and `schema = ModelConfig` in its body. `from_config`
  takes `config: Any`; annotate `config` in your own `from_config` to have it typed.
  omegakit no longer depends on `typing_extensions`.
- **Breaking:** `${secret:...}` wraps the interpolation that gives the secret, such
  as `${secret:${oc.env:TOKEN}}`, so a secret can come from any resolver. Replace
  every `${secret:NAME}` with `${secret:${oc.env:NAME}}`: the old form now gives the
  text `NAME` itself.
- **Breaking:** Error messages name a node by its dotted path, such as
  `items.0.model`, everywhere. Errors about `$base` and `$each` named a list
  item as `items0.model`, and errors from resolving, from overrides and from
  values inside a field as `items[0].model`.
- **Breaking:** Error messages share one style: keys and names in backticks,
  "mapping" rather than "dictionary", and "Cannot …". This changes the messages for
  a `$symbol` node with other keys, a `$base` or `$each` that is
  not a mapping, a missing attribute (``Module `m` has no attribute `x`.``), an
  include cycle, a `$partial` that is not a boolean, an `overrides` argument of the
  wrong type, and a missing PyTorch.
- **Breaking:** `omegakit check` and `omegakit show` take overrides as
  `--overrides KEY=VALUE ...`, and every other argument is a config file.
  They used to guess whether an argument was a file or an override. Replace
  `omegakit show app.yaml seed=3` with `omegakit show app.yaml --overrides seed=3`.
- `omegakit show --resolve` resolves `${secret:...}` to `***` instead of reading
  the secret and masking its text in the output. A value that another resolver
  builds from a secret, such as a number from `${oc.decode:${secret:...}}`, is
  masked now too; a copy of the secret's text that does not come from
  `${secret:...}` is no longer masked. The secret resolver no longer keeps the
  values it gives in memory.
- The API and Changelog pages moved into the folder of their section, Reference:
  `api/` is now `reference/api/`, and `changelog/` is now `reference/changelog/`.
- `omegakit check --schema` with something that is not a class exits with 2 once,
  instead of reporting every file as invalid.

### Removed

- **Breaking:** `generate_json_schema`, the `omegakit export-schema` command and the
  Editor support page. OmegaConf generates no JSON Schema, and omegakit adds
  nothing that OmegaConf does not support.
- **Breaking:** `check_schema`. A schema that does not fit its class's constructor
  now fails when the object is built, with the note that names the node.

### Fixed

- An `OSError` while a config file is read, such as an input/output error, passes
  through. It was reported as `ConfigFileSyntaxError`, as if the content were
  wrong.
- An error that a module raises while `validate` imports it, such as a
  `RuntimeError` or the `ModuleNotFoundError` of a missing dependency, gets a note
  that names the node. It passed without a place.
- A `$symbol` or `$target` may name a submodule that is not imported yet, such as
  `concurrent.futures`. It raised ``Module `concurrent` has no attribute
  `futures`.``
- `${paths:name}` raises for a name that was not registered. It resolved to
  `None`.
- `register_torch_device_resolver` no longer warns that the resolver cannot be
  inspected.
- An override that is no `key=value` raises `ConfigOverrideError`. `seed` used to
  set `seed` to `None`, `=5` created the key `''`, and `layers[0]=1` replaced the
  list `layers` with a mapping.
- An override whose value is an include, such as `model=~include big.yaml`, raises
  `ConfigOverrideError`. It stayed in the config as that text, since the includes
  are resolved before the overrides are applied.
- An override that cannot be applied is named in the message, as in ``Cannot apply
  `model.width=8`: ...``.
- An included text that ends up as a backslash before `${`, such as `\\${x}`, stays
  that text. The including config resolved it as an interpolation again.
- `omegakit check` and `omegakit show` print failures to stderr. They went to
  stdout, so `omegakit show app.yaml > out.yaml` wrote the error into the file.
- A schema field annotated with a bare `tuple` holds a `tuple`, as the Dataclass
  schemas page says, instead of a `list`.
- A list of overrides with an item that is not a string raises `ConfigOverrideError`, as
  overrides of the wrong type do, instead of OmegaConf's `ValueError`.
- A schema annotation that fails to evaluate, such as `"int | 1"`, raises
  `SchemaDefinitionError`, as the Dataclass schemas page says, instead of the
  `TypeError` or `SyntaxError` from evaluating it.
- The error for `$base` or `$each` references that form a cycle names only the
  nodes on the cycle, not the nodes that wait for it or contain it.
- `validate`, `instantiate` and `prepare` ignore `$meta` in the mapping of a data
  field, such as a nested dataclass or a `dict[str, int]`, as the Metadata page
  says, instead of rejecting it as an unknown field or a value of the wrong type.

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

[0.8.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.8.0
[0.7.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.7.0
[0.6.1]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.6.1
[0.6.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.6.0
[0.5.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.5.0
[0.4.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.4.0
[0.3.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.3.0
[0.2.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.2.0
[0.1.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.1.0
