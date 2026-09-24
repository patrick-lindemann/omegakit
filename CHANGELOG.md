# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - Unreleased

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

First release. omegakit is the configuration package from GraspDiff, extracted into
a standalone library. The configuration language is specified in the
[configuration contracts](https://omegakit.readthedocs.io/en/latest/contracts.html).

### Changed compared with the GraspDiff original

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

[0.2.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.2.0
[0.1.0]: https://github.com/patrick-lindemann/omegakit/releases/tag/v0.1.0
