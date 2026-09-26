# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

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

[0.5.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.5.0
[0.4.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.4.0
[0.3.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.3.0
[0.2.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.2.0
[0.1.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.1.0
