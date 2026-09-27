# Environment and trust

## Environment

- Importing `omegakit` or any of its modules has no side effects: no resolver is
  registered, and `torch` is not imported.
- omegakit does not load `.env` files.
- omegakit supports OmegaConf 2.3 and 2.4 (`omegaconf>=2.3,<2.5`) and behaves the
  same on both. Assembly uses private OmegaConf node APIs, so CI tests the lowest
  supported version, the locked version and the newest pre-release in the range.
- Configs import and call arbitrary Python objects. Load them only from trusted
  sources (see Trust below).

### Trust

Loading, validating, checking and showing a config are not safe on untrusted
input. Validation checks the shape of values; it is not input sanitisation. Code
and I/O happen without anything being built:

- The modules named by `$class` and `$ref` are imported, which runs their
  import-time code, unless `allowed_modules` limits them ([Validation](typed-configs.md#validation)). `allowed_modules`
  is not a sandbox.
- Resolvers run, including OmegaConf's `oc.env`, which reads any environment
  variable of the process. `load_config` itself evaluates interpolations in
  `~import` paths and in `$base` and `$defaults` values. An application that does
  not need `oc.env` can call `OmegaConf.clear_resolver("oc.env")` before loading.
- Every `default_factory` of a schema runs during validation ([Validation](typed-configs.md#validation)).
- `~import` reads any file the process can read, unless `import_root` is set ([Imports](assembly.md#imports)).
  `keep_targets=False` does not make loading safe.
- Overrides carry the same trust as the config file: an override can set `$class`,
  `$ref` and interpolations such as `${oc.env:...}`.
- The command line puts the working directory first on `sys.path` ([Command line](command-line.md#command-line)), so a
  module there can shadow a `$class` target.
- Reading a special file, such as a FIFO, blocks.
- `~import` fan-out can grow exponentially, because every import is a deep copy,
  and a long chain of `$base` references costs time quadratic in its size.
- Any string value that starts with `~import` is an import, so a tool that writes
  YAML from untrusted strings must not let them start with it.
- Error messages, and so CI logs, can contain scalar config values; mappings are
  described by their keys.

Resolved configs and objects built by `instantiate` contain the real values of
secrets read with `${oc.env:...}`. Log `mask_secrets(config)` instead of a resolved
config, and keep secrets out of arguments that components save, such as
hyperparameters written into checkpoints.

### Masking secrets

`mask_secrets(config, *, keys=())` takes an unresolved config, such as the result
of `load_config`, and returns it resolved as plain `dict`s and `list`s for logging,
with secrets replaced by `***`:

1. **By key.** A key is split into words at `_`, `-`, `.` and camelCase
   boundaries. It is secret when its words contain `password`, `passwd`, `pass`,
   `passphrase`, `secret`, `token`, `credential`, `auth`, `bearer`, `cookie`,
   `dsn`, `webhook` or `apikey`, or the sequences `api key`, `private key` or
   `access key`, each also in the plural. Whole words only: `pad_token` is
   secret, `tokenizer` is not. A secret key masks every value below it. `keys`
   adds entries, each a word or a space-separated sequence; the defaults stay.
2. **By environment variable.** A value whose unresolved text reads
   `${oc.env:NAME}`, also with spaces or nested in another interpolation, is
   masked when `NAME` is secret by the same rule: `DB_PASSWORD` is, `APP_ENV` and
   `PWD` are not.
3. **By value.** The resolved strings masked by 1 and 2 that are at least 8
   characters long are replaced by `***` inside every other string, longest first,
   such as a password inside a URL. Numbers and keys are never rewritten.

A masked value is resolved only to collect it for 3; if that fails, it is masked
anyway. A masked value that is not a string becomes the string `***`. A missing
value prints as `???`. Any other resolution error raises `ConfigValidationError`.

Not masked: a secret in a value whose key names no secret, a secret shorter than 8
characters used elsewhere, a secret used as a key, a value read by a resolver other
than `oc.env`, and objects built by `instantiate`. A secret equal to a common word
masks that word in every other string.

## Resolvers

- OmegaConf's own resolvers, such as `oc.env`, are always available:
  `${oc.env:NAME}` reads an environment variable and `${oc.env:NAME,default}` falls
  back to a default. omegakit does not register or change them.
- Resolvers are opt-in. Registration is global to OmegaConf, and an existing name
  raises unless `replace=True` is passed. `omegakit.resolvers` exports nothing:
  each resolver is imported from its own module, which carries its own
  dependencies.
- Resolvers are registered with the API of the installed OmegaConf
  (`register_resolver` on 2.4, `register_new_resolver` on 2.3), so neither warns.
