# Command line and editor schemas

## Command line

`omegakit` (also `python -m omegakit`) puts the working directory first on the
import path, so `$class`, `--schema` and `json-schema` paths resolve from there.

**Arguments.** `check` and `show` take config files and `key=value` overrides,
mixed in any order but before the options. An argument that names an existing file
is a config file, even with a `=`; otherwise it is an override if it has a `=` with
no `/` before it, else a config file (which then fails to load). Overrides apply to
every file. `--import-root DIR` passes `import_root` to `load_config`
([Imports](../guide/imports.md#rules)).

**Exit codes.** 0 on success; 1 when a config is invalid or cannot be loaded; 2 for
usage errors (no config file, an unknown option, a `--schema` or `json-schema` path
that cannot be imported, an `--import-root` that is not a directory).

- `omegakit check CONFIG... [KEY=VALUE...] [--schema IMPORT_PATH] [--allow-missing]
  [--allow-module NAME]... [--import-root DIR]` validates each file
  ([Validation](../guide/validation.md#rules)); each `--allow-module` adds an entry
  to `allowed_modules`. It prints `<file>: <exception type>: <message>` for each
  invalid file and nothing for valid ones. Any exception, and a `SystemExit` raised
  by an imported module, marks that file invalid, and the other files are still
  checked; `KeyboardInterrupt` stops the command.
- `omegakit show CONFIG [KEY=VALUE...] [--node KEY] [--resolve] [--keep-meta]
  [--show-secrets] [--import-root DIR]` prints the assembled config, or the node at
  `KEY`, as YAML; a scalar prints as its value.
  - `KEY` is a dotted path, walked as `~import file#node` is (`items.0.name`,
    `items.-1`). A node that does not exist, or a path through an interpolation
    without `--resolve`, exits with 1.
  - Without `--resolve`, values print as written (`${…}`, `???`, `null`). With it,
    interpolations on the path are followed and only the selected node is resolved;
    missing values print as `???`, and other resolution errors exit with 1 and one
    line.
  - Secrets are masked as by `mask_secrets` ([Logging without secrets](../security.md#logging-without-secrets)),
    using the whole config even with `--node`: by key always, by environment
    variable and by value with `--resolve`. `--show-secrets` turns masking off.
- `omegakit json-schema IMPORT_PATH [-o FILE] [--check]` prints or writes the JSON
  Schema. `--check` needs `-o`, writes nothing, and exits with 1 if `FILE` is
  missing or differs from the generated schema (compared as JSON).

## Editor schemas

`generate_json_schema(schema)` and `omegakit json-schema` produce a draft-07 JSON
Schema for YAML files, from a root schema dataclass or from a `Configurable` class
whose schema describes a fragment file.

- Any value, scalar or node, may also be `${…}`, `???` or an `~import`.
- Any mapping accepts `$` keys; other unknown keys are errors.
- Nothing is required: values may come from `$base`, `$defaults`, imports or
  overrides. `validate` reports what is missing.
- Enums list their member names, and the `str` and `int` values that are not also a
  name; `Literal` fields list their values; fixed-length tuples have one schema per
  position.
- An object field of a `Configurable` class with a dataclass schema is checked
  against that schema only when its `$class` is the class's defining module and
  qualified name; any other `$class` (a re-export, a subclass) accepts any mapping.
- No field descriptions are generated.
