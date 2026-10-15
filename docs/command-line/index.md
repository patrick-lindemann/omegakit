# Overview

Installing omegakit adds the `omegakit` command, also available as
`python -m omegakit`. It works on config files without writing a script:

- [`check`](check/index.md) validates config files, for a quick look before a run,
  a pre-commit hook or CI.
- [`show`](show/index.md) prints a config as `load_config` assembles it, and the
  values a run will get.

Run it from the directory that your `$target` and `$symbol` paths import from, as
your own scripts do: the command puts the working directory first on `sys.path`.
It registers the `${secret:...}` resolver ([Secrets](../security/secrets/index.md)).
`omegakit <command> --help` lists a command's options, and `omegakit --version`
prints the installed version.

The examples in this section run in the directory of the example project, a small
PyTorch project. Its experiment files are in `configs/experiments` and extend
`configs/base.yaml`, whose root names the dataclass `project.Experiment` with
`$target`. An experiment has a name, seed, run directory, data, model, optimizer,
loss, and `epochs: int` ([Getting started](../getting-started/index.md)).
