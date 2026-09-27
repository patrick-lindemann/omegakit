# Command line and editor schemas

## Command line

The `omegakit` command (also `python -m omegakit`) has one subcommand per task. It
puts the working directory on the import path, so `$class`, `--schema` and
`json-schema` import paths resolve from there.

**Arguments.** `check` and `show` take config files and `key=value` overrides in
any order. An argument that names an existing file is a config file, even if it
contains `=`. Otherwise it is an override if it has a `=` with no `/` before it, and
a config file (which then fails to load) if not. Overrides apply to every file.
Their `--import-root DIR` passes `import_root` to `load_config` ([Imports](assembly.md#imports)).

**Exit codes.** 0 on success, 1 when a config is invalid or cannot be loaded, 2 for
usage errors (a missing config file, an unknown option, an `--schema` or
`json-schema` import path that cannot be imported, an `--import-root` that is not a
directory).

- `omegakit check CONFIG... [KEY=VALUE...] [--schema IMPORT_PATH] [--allow-missing]
  [--allow-module NAME]... [--import-root DIR]`
  loads each file with the overrides and validates it ([Validation](typed-configs.md#validation)). Each `--allow-module`
  adds an entry to `allowed_modules` ([Validation](typed-configs.md#validation)); without one, every module is allowed. It prints one line per
  failing file, `<file>: <exception type>: <message>`, and nothing for valid files.
  Every exception from loading or validating counts as a failure of that file, and
  so does a `SystemExit` raised by a module that is imported; the other files are
  still checked. `KeyboardInterrupt` stops the command.
- `omegakit show CONFIG [KEY=VALUE...] [--node KEY] [--resolve] [--keep-meta]
  [--show-secrets] [--import-root DIR]`
  prints the assembled config as YAML, or the node at `KEY`. `KEY` is a dotted path
  with the same syntax and walk as `~import file#node` ([Imports](assembly.md#imports)): `items.0.name`, and
  `items.-1` from the end. The node is printed unresolved: an interpolation prints
  as written, `???` as `???` and `null` as `null`. A path that goes through an
  interpolation, or a node that does not exist, exits with 1. `--resolve` follows
  interpolations on the path, and resolves only the selected node (the whole config
  without `--node`); missing values print as `???`, and any other resolution error
  exits with 1 and one line, like a load error. A scalar node prints as its value.
  Secrets are masked as by `mask_secrets` ([Environment](environment.md#environment)), with the secrets of the whole
  config, even with `--node`: by key in every mode, and by environment variable and
  by value with `--resolve`. `--show-secrets` turns masking off.
- `omegakit json-schema IMPORT_PATH [-o FILE] [--check]` prints or writes the JSON
  Schema ([Editor schemas](#editor-schemas)). With `--check`, which needs `-o`, it writes nothing and exits with 1
  if `FILE` is missing or differs from the generated schema (compared as JSON).

## Editor schemas

`generate_json_schema(schema)` and the command `omegakit json-schema` ([Command line](#command-line))
generate a JSON Schema (draft-07) for YAML files. The argument is a root schema
dataclass ([Validation](typed-configs.md#validation)), or a `Configurable` class whose schema describes a fragment file.

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
