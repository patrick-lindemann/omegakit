# Comparison to other libraries

Checked on 2026-09-27 against [Hydra](https://pypi.org/project/hydra-core/) 1.3.7,
[hydra-zen](https://pypi.org/project/hydra-zen/) 0.16.0,
[jsonargparse](https://pypi.org/project/jsonargparse/) 4.52.0,
[Lightning](https://pypi.org/project/lightning/) 2.6.6,
[Fiddle](https://pypi.org/project/fiddle/) 0.3.0,
[gin-config](https://pypi.org/project/gin-config/) 0.5.0,
[ml_collections](https://pypi.org/project/ml-collections/) 1.1.0,
[Sacred](https://pypi.org/project/sacred/) 0.8.7 and
[OmegaConf](https://pypi.org/project/omegaconf/) 2.3.1, the latest releases on
PyPI that day.

What omegakit leaves to you is listed on
[Reproducible runs](../reproducible-runs/index.md#what-omegakit-does-not-do). It
also parses no command line: your entrypoint passes the arguments to `load_config`
as overrides, which change values but cannot add a file.

## Hydra

- Both build on OmegaConf and build objects from YAML: `_target_` and `_partial_`
  in Hydra's [`instantiate`](https://hydra.cc/docs/advanced/instantiate_objects/overview/),
  `$class`, `$partial` and `$ref` in omegakit.
- Composition: Hydra picks options from
  [config groups](https://hydra.cc/docs/tutorials/basic/your_first_app/config_groups/)
  through a [defaults list](https://hydra.cc/docs/advanced/defaults_list/), also
  from the command line: `db=postgresql` chooses an option, and
  [`+db=mysql`](https://hydra.cc/docs/advanced/override_grammar/basic/) adds one.
  omegakit uses explicit paths instead: an experiment file names its base with
  `$base: ~import ../base.yaml` and its parts with `~import`, and there is one file
  per experiment.
- Hydra runs your entrypoint through `@hydra.main` and does more around it:
  - [`--multirun`](https://hydra.cc/docs/tutorials/basic/running_your_app/multi-run/)
    sweeps, with launchers such as [joblib](https://hydra.cc/docs/plugins/joblib_launcher/),
    [submitit](https://hydra.cc/docs/plugins/submitit_launcher/) for SLURM and
    [Ray](https://hydra.cc/docs/plugins/ray_launcher/), and sweepers such as
    [Optuna](https://hydra.cc/docs/plugins/optuna_sweeper/) and
    [Ax](https://hydra.cc/docs/plugins/ax_sweeper/);
  - an [output directory per run](https://hydra.cc/docs/tutorials/basic/running_your_app/working_directory/)
    that saves the composed config and the overrides in `.hydra/`. Since Hydra 1.2
    it no longer changes the working directory by default;
  - [logging](https://hydra.cc/docs/tutorials/basic/running_your_app/logging/)
    configuration and
    [tab completion](https://hydra.cc/docs/tutorials/basic/running_your_app/tab_completion/);
  - choosing the config file on the command line with
    [`--config-name`](https://hydra.cc/docs/advanced/hydra-command-line-flags/).

  The [Compose API](https://hydra.cc/docs/advanced/compose_api/) works without the
  decorator, and gives up multirun, tab completion, and working directory and
  logging management.
- Checking: Hydra's
  [structured configs](https://hydra.cc/docs/tutorials/structured_config/intro/)
  check types when a config is composed or changed. omegakit checks each `$class`
  node whose class has a schema, and each object field against the class it
  expects, before anything is built. It also generates JSON Schemas for editors,
  and has `omegakit check` for CI.
- Use Hydra if you want the command line to compose configs, cluster launchers or
  managed run directories.
  [hydra-zen](https://mit-ll-responsible-ai.github.io/hydra-zen/) generates Hydra
  configs from Python signatures with `builds`, and wraps task functions with
  `zen`.

## jsonargparse and LightningCLI

- [jsonargparse](https://jsonargparse.readthedocs.io/en/stable/) derives a command
  line and config files (YAML, JSON, TOML, Jsonnet) from type hints and
  docstrings, and builds classes from `class_path` and `init_args`. The signatures
  come first; in omegakit the config files come first.
- [LightningCLI](https://lightning.ai/docs/pytorch/stable/cli/lightning_cli_intermediate.html)
  is built on jsonargparse for PyTorch Lightning. It configures the model, the data
  module and the trainer, and
  [saves the config of each run](https://lightning.ai/docs/pytorch/stable/cli/lightning_cli_advanced.html)
  as `config.yaml` in its log directory. Use it when you train with Lightning.

## Fiddle, gin-config and ml_collections

These keep configs in Python:

- [Fiddle](https://fiddle.readthedocs.io/en/latest/) describes a call as a Python
  object, `fdl.Config` or `fdl.Partial`, and `fdl.build` builds a nested config.
  Its last release on PyPI is from April 2024.
- [gin-config](https://github.com/google/gin-config) binds the parameters of
  functions marked `@gin.configurable` from `.gin` files, and
  `gin.operative_config_str()` gives the values a run used. Its last release is
  from November 2021.
- [ml_collections](https://ml-collections.readthedocs.io/en/latest/) holds a config
  in a `ConfigDict`, loads it from a Python file with
  [`config_flags`](https://ml-collections.readthedocs.io/en/latest/config_flags.html),
  and takes overrides such as `--config.lr=0.1`.

A Python config can compute anything, and runs when it is loaded. An omegakit file
is YAML data that names the classes to build. Loading it imports no module, and
validating it imports the modules it names but calls none of their classes
([Trust model](../security/trust-model/index.md)).

## Sacred

- [Sacred](https://sacred.readthedocs.io/en/stable/experiment.html) wraps an
  experiment in an `Experiment` object, with config scopes, captured functions and
  command-line updates such as `with seed=123`.
- Its [observers](https://sacred.readthedocs.io/en/stable/observers.html) record
  each run's config, together with the
  [source files, dependencies, git state and host](https://sacred.readthedocs.io/en/stable/collected_information.html),
  and it [seeds](https://sacred.readthedocs.io/en/stable/randomness.html) Python's,
  NumPy's and PyTorch's generators for you.
- omegakit records none of this and seeds nothing. Use Sacred if you want each run
  recorded and seeded for you.

## OmegaConf

- [OmegaConf](https://omegaconf.readthedocs.io/en/2.3_branch/) provides merging,
  interpolation, custom resolvers and structured configs. `load_config` returns its
  `DictConfig`.
- It does not build objects or import files by path. Use it alone if you build
  everything yourself.
