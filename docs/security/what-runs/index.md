# What runs

omegakit is not meant for untrusted configs. A config names classes to import and
call, reads environment variables and imports other files. Treat a config file like
a Python file: load it only from sources you trust.

- `load_config` reads every file that an `~import` names, and resolves the
  interpolations in `~import` paths and in `$base` and `$defaults` values. So
  resolvers already run while loading, and `keep_targets=False` does not make
  loading safe.
- `validate`, `instantiate`, `prepare` and `omegakit check` resolve every
  interpolation, and `omegakit show --resolve` resolves the node it prints and
  every secret value. So every resolver can run. `oc.env` reads any environment
  variable. Call `OmegaConf.clear_resolver("oc.env")` before loading if you do
  not need it.
- Validating and building import the modules that `$class` and `$ref` name, which
  runs their import-time code. Validation calls no configured class, but some
  code of the schemas and imported classes still runs
  ([Validation](../../objects/validation/index.md#rules)).
- Building calls the classes and functions the config names.
- Overrides carry the same trust as the files. An override can set `$class` or
  `$ref`, or read an environment variable. Never build overrides from requests or
  other untrusted input.
- The command line puts the working directory first on `sys.path`, so a module
  there can shadow a `$class` target.
- Validation checks the shape of values. It is not input sanitisation.
- Any string that starts with `~import` is an import. YAML written from untrusted
  strings must not let a value start with it.
- Reading a special file, such as a FIFO, blocks.
- `~import` fan-out can grow exponentially, because every import is a deep copy,
  and a long `$base` chain costs time quadratic in its length.
- Error messages, and so CI logs, can contain scalar config values. Mappings are
  described by their keys.

## Checking configs in CI

`omegakit check` runs the code listed above, so:

- In CI, check your own branches. Do not run it in a `pull_request_target`
  workflow, which runs with your repository's secrets on a fork's files.
- Do not run pull requests from forks on self-hosted runners.
- Pass `--allow-module` for your own packages and `--import-root` for your config
  directory, to limit what a file can reach.
