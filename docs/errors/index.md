# Errors

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
| `$class`/`$ref` in a module that `allowed_modules` does not allow ([Security](../security/index.md#allowed-modules)) | `ConfigValidationError` | the path, the node and `allowed_modules` |
| `allowed_modules` given as a string | `TypeError` | `not the string` |
| Raw dict value that OmegaConf does not support | `UnsupportedValueType` | the key |
| Unknown `$` key, or `$class` with `$ref`, at validation or instantiation | `ConfigValidationError` | the key and `reserved` |
| `$partial` not a boolean | `ConfigValidationError` | `$partial` |
| `???` accessed | `MissingMandatoryValue` | the full key |
| Unresolvable `${…}` accessed | `InterpolationKeyError` (or another OmegaConf error) | the key |
| `???`, unresolvable `${…}` or a failing resolver, validated or instantiated | `ConfigValidationError`, caused by OmegaConf's error | `Cannot resolve` and the full key |
| Exception from a constructor or `from_config` | unchanged | original message, plus the note from [Building objects](../guide/building-objects/index.md#rules) |
| Schema outside the supported subset ([Typed configs](../guide/typed-configs/index.md#rules)) | `ConfigValidationError` | the field and the fix |
| Schema that does not match `__init__` ([Typed configs](../guide/typed-configs/index.md#rules)) | `ConfigValidationError` | the field or parameter |
| Unknown field, missing required field, or invalid native value | `ConfigValidationError` | the node path and the schema |
| Object field whose `$class` is not the annotated class or a subclass, or a `$ref` that is not an instance | `ConfigValidationError` | the field path, the expected class and the given node |
| `make_node()` for a class or function not defined at module level | `ValueError` | `module level` |
| Type variable in a `Configurable` base that cannot be substituted | `TypeError` | `Cannot resolve type variable` |
| Resolver registered twice without `replace=True` | `ValueError` | `already registered` |
| Registering a library's resolvers without that library installed | `ImportError` | the library to install |

A malformed dotlist override such as `["a"]` is not an error: OmegaConf sets `a` to
`None`.
