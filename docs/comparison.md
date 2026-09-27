# Compared with other libraries

Checked on 2026-09-27 against Hydra 1.3.7, hydra-zen 0.16.0, jsonargparse 4.52.0,
Lightning 2.6.6, pydantic-settings 2.15.0, Dynaconf 3.3.5 and OmegaConf 2.3.1. Each
statement about another library links to the page it comes from.

## Hydra

[Hydra](https://hydra.cc/docs/1.3/intro/) describes itself as "an open-source Python
framework that simplifies the development of research and other complex
applications". It is the closest relative of omegakit: both build on OmegaConf, and
both build objects from YAML.

**Hydra is a framework.** Your entrypoint is a function decorated with
`@hydra.main`, and Hydra runs it. It creates an
[output directory for each run](https://hydra.cc/docs/1.3/tutorials/basic/running_your_app/working_directory/),
writes the composed config and the overrides there, and
[logs to the console and a file in it](https://hydra.cc/docs/1.3/tutorials/basic/running_your_app/logging/).
Since `version_base` 1.2 it
[no longer changes the working directory](https://hydra.cc/docs/1.3/upgrades/1.1_to_1.2/changes_to_job_working_dir/)
by default. `--multirun` runs the function once per combination of values, and
[sweeper and launcher plugins](https://hydra.cc/docs/1.3/advanced/plugins/overview/)
choose the combinations and run the jobs elsewhere. Without the decorator, the
[Compose API](https://hydra.cc/docs/1.3/advanced/compose_api/) (`initialize` and
`compose`) builds a config anywhere, for example in tests, but Hydra's docs advise
against it where `@hydra.main` fits, because it gives up multirun, working
directory and logging management.

**omegakit is a library.** You call `load_config` from your own `main()`, and
nothing happens to your working directory, your logging or your command line
unless you do it.

**Composition differs.** Hydra composes a config from
[config groups and the defaults list](https://hydra.cc/docs/1.3/intro/): a group
such as `db` holds one file per option, and the defaults list picks one. omegakit
composes by file path: `~import` pastes in another file or one of its nodes, and
`$base` and `$defaults` merge shared settings under any node, not only at the top
of a file.

**Building objects.** Hydra's
[`instantiate`](https://hydra.cc/docs/1.3/advanced/instantiate_objects/overview/)
reads `_target_`, with `_partial_` for a `functools.partial` and nested nodes built
recursively. omegakit's `$class`, `$partial` and `$ref` do the same jobs.
[Structured configs](https://hydra.cc/docs/1.3/tutorials/structured_config/intro/)
give Hydra runtime type checking as a config is composed or changed. What omegakit
adds is a check of the whole node before any configured object is built: every
`$class` is checked against the schema of the class it names, and against the class
that the field expects, including subclasses. On top of that come typed
`Configurable` classes, JSON Schemas for YAML editors, and `omegakit check` for CI.

**For untrusted input** omegakit has two limits, not guarantees: `allowed_modules`
restricts the modules a config can name, and `mask_secrets` hides secrets when you
log a config. Neither makes an untrusted config safe to load; see
[Trust](contracts.md#trust).

**When to pick Hydra instead:** for parameter sweeps and launching jobs to other
machines, for its plugin ecosystem, and for choosing config options from the
command line (`db=postgres`). [hydra-zen](https://mit-ll-responsible-ai.github.io/hydra-zen/)
generates Hydra's dataclass configs from your code, if you want to keep Hydra and
write fewer YAML files.

## OmegaConf

[OmegaConf](https://omegaconf.readthedocs.io/en/2.3_branch/) is the
"YAML based hierarchical configuration system" underneath omegakit: merging,
interpolation and structured configs with runtime type safety all come from it, and
`load_config` returns an OmegaConf `DictConfig`. OmegaConf does not build objects
or compose files by path. Use it alone when you want a config object and build
everything yourself.

## jsonargparse and LightningCLI

[jsonargparse](https://jsonargparse.readthedocs.io/en/stable/) builds command-line
interfaces from the type hints of your functions and classes, and reads JSON, YAML,
TOML and Jsonnet config files. Classes are chosen with `class_path` and
`init_args` and then instantiated. The CLI and the config come from your
signatures. In omegakit the config comes first and the command line only
overrides it. [LightningCLI](https://github.com/Lightning-AI/pytorch-lightning/blob/master/docs/source-pytorch/cli/lightning_cli_advanced.rst)
is built on jsonargparse for PyTorch Lightning: it configures the model, the data
module and the trainer, and saves the full config to each run's log directory.
Pick it when you train with Lightning.

## pydantic-settings

[pydantic-settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/)
loads a pydantic model's fields from environment variables, `.env` files, secrets
directories and cloud secret stores, and, with
[extra sources](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/),
from JSON, TOML and YAML files, all validated by pydantic. The result is one
settings object; building the classes that a config names is not among its
documented features. Pick it for settings that come mostly from the environment.

## Dynaconf

[Dynaconf](https://www.dynaconf.com/) manages settings from TOML, YAML, JSON, INI
and Python files, with environment variables and `.env` files overriding them,
optional layered environments (`development`, `production`), validators, secrets in
Vault or Redis, and extensions for Django and Flask. Its
[environments](https://www.dynaconf.com/settings_files/) are sections of the same
settings files (`[development]`, `[production]`), where omegakit uses one file per
environment on top of a shared base. Building objects from the config is not among
its documented features. Pick it for settings in a Django or Flask application.
