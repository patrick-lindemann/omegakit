# Trust model

omegakit is not meant for untrusted configs. A config names modules to import and
classes to call, reads environment variables and includes other files. Treat a
config file like a Python file: load it only from sources you trust.

In research, configs travel with results: a checkpoint downloaded with its config, a
colleague's run directory, the config published with a paper. The Rules below list
what loading, checking and building such a config runs. Nothing limits which
modules `$target` and `$symbol` import, so read a config before you load it.

## Checking configs in CI

`omegakit check` runs the code listed under Rules, so:

- In CI, check your own branches. Do not run it in a `pull_request_target`
  workflow, which runs with your repository's secrets on a fork's files.
- Do not run pull requests from forks on self-hosted runners.
- Pass `--include-root` with your config directory, so that no file can include a
  file outside it.

## Rules

- `load_config` reads every file that an `~include` names, each once per load, and
  resolves the interpolations of `~include` values and of `$base` and `$each`
  values ([Loading](../../guide/loading/index.md#rules)). So resolvers already run
  while loading.
- `validate`, `is_valid`, `instantiate`, `prepare` and `omegakit check` resolve
  every interpolation, and `omegakit show --resolve` resolves the node it prints.
  So every resolver can run. `oc.env` reads any environment variable. Call
  `OmegaConf.clear_resolver("oc.env")` before loading if you do not need it.
- Checking imports every module that `$target` and `$symbol` name, which runs its
  top-level code, and runs the `__instancecheck__` and `__subclasscheck__` of the
  classes in a schema ([Validation](../../schemas/validation/index.md#rules)).
  `instantiate` and `prepare` check first, then call the classes and functions that
  `$target` names.
- Nothing limits which modules are imported: any module on `sys.path` can be named.
  `include_root` limits only which files `~include` reads
  ([Includes](../../guide/includes/index.md#rules)).
- Overrides carry the same trust as the files. An override can set `$target` or
  `$symbol`, as in `model.$target=other.Model`, or read an environment variable.
  Never build overrides from requests or other untrusted input.
- The command line puts the working directory first on `sys.path`, so a module
  there can shadow the module that a `$target` names.
- Checking compares values with their schema. It is not input sanitisation.
- Every string that starts with `~include` and a space is an include. YAML written
  from untrusted strings must not let a value start with it.
- Reading a special file, such as a FIFO, blocks.
- Each file is read once per load, but every include is a copy of its own: a file
  that includes another twice, which includes a third twice, holds four copies of
  the third. The assembled config can grow exponentially with the depth of the
  includes.
- Error messages, and so CI logs, can quote config values. Mask secrets in what
  `omegakit show` prints with `${secret:...}` ([Secrets](../secrets/index.md)).
