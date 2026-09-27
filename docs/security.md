# Security

omegakit is not meant for untrusted configs. A config names classes to import and
call, reads environment variables and imports other files. Treat a config file like
a Python file: load it only from sources you trust.

## What runs

- `load_config` reads every file that an `~import` names, and resolves the
  interpolations in `~import` paths and in `$base` and `$defaults` values. So
  resolvers already run while loading, and `keep_targets=False` does not make
  loading safe.
- `validate`, `instantiate`, `prepare`, `omegakit check` and
  `omegakit show --resolve` resolve every interpolation, so every resolver runs.
  `oc.env` reads any environment variable. Call
  `OmegaConf.clear_resolver("oc.env")` before loading if you do not need it.
- Validating and building import the modules that `$class` and `$ref` name, which
  runs their import-time code. Validation calls no configured class, but it runs
  the `__instancecheck__` and `__subclasscheck__` of imported classes and every
  `default_factory` of a schema, possibly several times. A factory's exception
  propagates.
- Building calls the classes and functions the config names.
- Overrides carry the same trust as the files. An override can set `$class` or
  `$ref`, or read an environment variable. Never build overrides from requests or
  other untrusted input.
- The command line puts the working directory first on `sys.path`, so a module
  there can shadow a `$class` target.
- Validation checks the shape of values. It is not input sanitisation.

Some smaller points:

- Any string that starts with `~import` is an import. YAML written from untrusted
  strings must not let a value start with it.
- Reading a special file, such as a FIFO, blocks.
- `~import` fan-out can grow exponentially, because every import is a deep copy,
  and a long `$base` chain costs time quadratic in its length.
- Error messages, and so CI logs, can contain scalar config values. Mappings are
  described by their keys.

## Limits

Two settings limit what a config can reach. They are limits, not a sandbox: a
config that passes them still runs code.

### Allowed modules

`validate`, `instantiate` and `prepare` take `allowed_modules`, and
`omegakit check` takes `--allow-module NAME`, repeatable. They limit which modules
`$class` and `$ref` may name. [Building objects](guide/building-objects.md) shows
an override that is rejected.

- `None`, the default, allows every module, and `[]` none. Any iterable of module
  names works and is read once. A `str` raises `TypeError`.
- An entry allows that module and its submodules: `["webapp", "torch.optim"]`
  allows `webapp.db.Postgres` and `torch.optim.Adam`, but not `webapp_evil.X` or
  `torch.load`. An entry that names a class allows nothing. `$ref: math.pi` needs
  `"math"`.
- Every node the validation walk reaches is checked, including nodes under `Any`,
  `Callable`, `list` and `dict` fields. Before importing, the module part of the
  path is checked, so a module that is not allowed never runs; its parent packages
  are still imported. After importing, the object's `__module__` is checked, if it
  has one. The second check rejects a name that an allowed module imported from
  elsewhere, such as `pkgx.db.run` for `from subprocess import run`, and accepts
  re-exports within an allowed package.
- A failing path raises `ConfigValidationError` naming the path and the node.
- Allowing `builtins`, `importlib`, `os`, `subprocess`, `shutil` or `pickle` equals
  no restriction, because of `builtins.__import__` and `builtins.open`.
- Not covered: resolvers, the `schema` argument and `--schema`, `json-schema`
  paths, and `instantiate` calls inside your own `from_config`.

### Import root

`load_config` takes `import_root`, and `omegakit check` and `omegakit show` take
`--import-root DIR`. An `~import` of a file outside that directory raises
`ConfigValidationError`, after interpolations and symbolic links are resolved. The
root file itself is not checked. [Imports](guide/imports.md) shows an example. The
default allows any file the process can read.

## Checking configs in CI

`omegakit check` runs code from the files it checks, as described above. Run it on
trusted content only:

- In CI, check your own branches. Do not run it in a `pull_request_target`
  workflow, which runs with your repository's secrets on a fork's files.
- Do not run pull requests from forks on self-hosted runners.
- Pass `--allow-module` for your own packages and `--import-root` for your config
  directory, to limit what a file can reach.

## Logging without secrets

A resolved config holds the real value of every secret, and so do the objects built
from it. Log `mask_secrets(config)` instead:

```{literalinclude} examples/guide/security/main.py
:language: python
:caption: main.py
```

```text
s3cr3t-from-the-vault
$class: webapp.server.Server
host: 0.0.0.0
port: 8000
workers: 8
secret_key: '***'
```

`mask_secrets(config, keys=["salt"])` adds your own words to the list below.
`omegakit show` masks the same way. Keep secrets out of arguments that components
save, such as hyperparameters in checkpoints.

Masking is a safety net, not a guarantee. It cannot see a secret under a key that
names no secret, a secret shorter than 8 characters used inside another value, a
secret used as a key, a value from a resolver other than `oc.env`, or a built
object. A secret equal to a common word masks that word in every other string.

### Rules

`mask_secrets(config, *, keys=())` takes an unresolved config and returns it
resolved as plain dictionaries and lists, with secrets replaced by `***`. A value is
masked in three ways:

1. **By key.** Keys are split into words at `_`, `-`, `.` and camelCase. A key is
   secret if its words contain `password`, `passwd`, `pass`, `passphrase`,
   `secret`, `token`, `credential`, `auth`, `bearer`, `cookie`, `dsn`, `webhook`,
   `apikey`, or the sequences `api key`, `private key` or `access key`, also in
   the plural. Only whole words count: `pad_token` is secret, `tokenizer` is not.
   A secret key masks everything below it. `keys` adds words or space-separated
   sequences to this list.
2. **By environment variable.** A value whose unresolved text reads
   `${oc.env:NAME}`, also with spaces or nested, is masked if `NAME` is secret by
   the same rule: `DB_PASSWORD` is, `APP_ENV` and `PWD` are not.
3. **By value.** Every resolved string masked by rule 1 or 2 with at least 8
   characters is replaced by `***` inside every other string, longest first.
   Numbers and keys are never rewritten.

A masked value is resolved only to collect it for rule 3, and stays masked if that
fails. A masked value that is not a string becomes the string `***`. Missing values
print as `???`. Any other resolution error raises `ConfigValidationError`.
