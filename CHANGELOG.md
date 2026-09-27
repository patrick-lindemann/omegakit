# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- A Dataclass schemas page: a plain dataclass as the schema of a config, its field
  kinds and how a node is checked.
- A Reproducible runs page: seeding, one directory per run, saving the config and
  the overrides, and what omegakit does not do.
- A Parameter sweeps recipe: one run per combination of a few values.

### Changed

- **Breaking:** `instantiate` and `prepare` take the class of the result as the
  keyword-only `schema=` instead of the positional `expected`. Write
  `instantiate(config, schema=App)` for `instantiate(config, App)`. `schema` is now
  checked: a root with `$class` must name `schema` or a subclass, and a root without
  `$class` is built as `schema`, so a plain root dataclass gives a typed result.
- The documentation presents omegakit for reproducible experiments. The landing
  page and the sidebar are reorganised: Command line is in the top group, and
  Schemas is its own section.
- The Command line page moved from `tools/command-line/` to `command-line/`.
- The Validation page moved from `objects/validation/` to `schemas/validation/`.
- The Editor support page moved from `tools/editor-support/` to
  `schemas/editor-support/`.
- Resolvers have their own section, with an overview and a page per resolver
  module. The Resolvers guide page moved to `resolvers/overview/`.
- Security is split into three pages: Trust model, Restricting imports and Masking
  secrets. The Security page moved to `security/trust-model/`.
- The Errors page is removed. The Rules section of each feature page names the
  errors of its feature.
- The guide is split into three sections in the order you meet them: Configs,
  Building objects and Tools. Page URLs changed, for example `guide/loading/` is now
  `configs/loading/`.
- Overrides, environment variables, interpolation and missing values each have
  their own page. Base is now Inheritance, Defaults is now Shared defaults,
  Building objects is now Instantiation, Typed configs is now Schemas, and Editor
  schemas is now Editor support. The recipes have shorter titles, and their URLs
  follow them.

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
[configuration contracts](https://omegakit.readthedocs.io/en/latest/contracts.html).

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

[0.6.1]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.6.1
[0.6.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.6.0
[0.5.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.5.0
[0.4.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.4.0
[0.3.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.3.0
[0.2.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.2.0
[0.1.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.1.0
