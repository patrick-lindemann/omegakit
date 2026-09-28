# Overview

Installing omegakit adds the `omegakit` command, also available as
`python -m omegakit`. It works on config files without writing a script:

- [`check`](check/index.md) validates config files, for a quick look before a run,
  a pre-commit hook or CI.
- [`show`](show/index.md) prints a config as `load_config` assembles it, and the
  values a run will get.
- [`export-schema`](export-schema/index.md) writes the JSON Schema of a class, for
  your editor.

Run it from the directory that your `$class` paths import from, as your own
scripts do. `omegakit <command> --help` lists a command's options.

The examples in this section run in the directory of the example project, a small
PyTorch project. Its experiment files are in `configs/experiments` and extend
`configs/base.yaml`, and the dataclass `project.Experiment` describes an experiment:
its name, seed, run directory, data, model, optimizer, loss, and `epochs: int`.

## Rules

`omegakit` puts the working directory first on the import path, so `$class`,
`--schema` and `export-schema` paths resolve from there.

**Arguments.** `check` and `show` take config files and `key=value` overrides,
mixed in any order, all before or all after the options. Options between them are
a usage error. An argument that names an existing file is a config file, even with
`=` in it. Any other argument with `=` before the first `/` is an override.
Everything else is treated as a config file and fails to load. Overrides apply to
every file.

**Exit codes.** 0 on success. 1 when a config is invalid or cannot be loaded. 2 for
a usage error: no config file, an unknown option, a `--schema` or `export-schema`
path that cannot be imported, or an `--import-root` that is not a directory.

**Resolvers.** The command registers `${secret:...}` for `check` and `show`
([Secrets](../security/secrets/index.md)). Other resolvers, such as your own, are
not registered, so a config that uses them fails to resolve.
