# Compared with other libraries

Checked on 2026-09-27 against Hydra 1.3.7, hydra-zen 0.16.0, jsonargparse 4.52.0,
Lightning 2.6.6, pydantic-settings 2.15.0, Dynaconf 3.3.5 and OmegaConf 2.3.1.

## Hydra

- Both build on OmegaConf and build objects from YAML: `_target_`, `_partial_` in
  Hydra's [`instantiate`](https://hydra.cc/docs/1.3/advanced/instantiate_objects/overview/);
  `$class`, `$partial`, `$ref` in omegakit.
- Hydra runs your entrypoint through `@hydra.main` and manages
  [an output directory per run](https://hydra.cc/docs/1.3/tutorials/basic/running_your_app/working_directory/)
  and [logging](https://hydra.cc/docs/1.3/tutorials/basic/running_your_app/logging/).
  Since `version_base` 1.2 it
  [no longer changes the working directory](https://hydra.cc/docs/1.3/upgrades/1.1_to_1.2/changes_to_job_working_dir/)
  by default. The [Compose API](https://hydra.cc/docs/1.3/advanced/compose_api/)
  works without the decorator, but without multirun, working directory and logging
  management. omegakit is called from your own `main()` and changes none of these.
- Composition: Hydra selects options from
  [config groups through the defaults list](https://hydra.cc/docs/1.3/intro/);
  omegakit imports files by path (`~import`) and merges under any node
  (`$base`, `$defaults`).
- Checking: Hydra's
  [structured configs](https://hydra.cc/docs/1.3/tutorials/structured_config/intro/)
  check types when a config is composed or changed. omegakit checks every `$class`
  node against its class's schema, and against the class the field expects,
  before anything configured is built. It also generates JSON Schemas for editors
  and has `omegakit check` for CI.
- Use Hydra for `--multirun` sweeps,
  [sweeper and launcher plugins](https://hydra.cc/docs/1.3/advanced/plugins/overview/),
  and choosing config options on the command line (`db=postgres`).
  [hydra-zen](https://mit-ll-responsible-ai.github.io/hydra-zen/) generates Hydra
  configs from Python code.

## OmegaConf

- [OmegaConf](https://omegaconf.readthedocs.io/en/2.3_branch/) provides merging,
  interpolation and structured configs; `load_config` returns its `DictConfig`.
- It does not build objects or import files by path. Use it alone if you build
  everything yourself.

## jsonargparse and LightningCLI

- [jsonargparse](https://jsonargparse.readthedocs.io/en/stable/) derives a command
  line and config files (JSON, YAML, TOML, Jsonnet) from your type hints, and builds
  classes from `class_path` and `init_args`. The signatures come first; in omegakit
  the config files come first.
- [LightningCLI](https://github.com/Lightning-AI/pytorch-lightning/blob/master/docs/source-pytorch/cli/lightning_cli_advanced.rst)
  is jsonargparse for PyTorch Lightning: it configures the model, the data module
  and the trainer, and saves the config of each run. Use it when you train with
  Lightning.

## pydantic-settings

- [pydantic-settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/)
  fills one pydantic model from environment variables, `.env` files, secret stores
  and, with [extra sources](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/),
  JSON, TOML or YAML files.
- Building the classes a config names is not among its documented features. Use it
  for settings that come mostly from the environment.

## Dynaconf

- [Dynaconf](https://www.dynaconf.com/) reads TOML, YAML, JSON, INI and Python
  files, with overrides from environment variables and `.env`, validators, Vault and
  Redis for secrets, and Django and Flask extensions.
- Its [environments](https://www.dynaconf.com/settings_files/) are sections of the
  same files (`[development]`, `[production]`); omegakit uses a file per environment
  on a shared base.
- Building objects from the config is not among its documented features. Use it for
  settings in a Django or Flask application.
