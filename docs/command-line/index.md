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
