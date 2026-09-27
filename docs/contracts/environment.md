# Environment and trust

## Environment

- Importing `omegakit` or any of its modules registers no resolver and does not
  import `torch`. omegakit does not load `.env` files.
- OmegaConf 2.3 and 2.4 are supported (`omegaconf>=2.3,<2.5`), with the same
  behaviour. Assembly uses private OmegaConf node APIs, so CI tests the lowest
  supported, the locked and the newest pre-release versions.

### Trust

Loading, validating, checking and showing a config are not safe on untrusted input.
Validation checks the shape of values; it is not input sanitisation.

- Modules named by `$class` and `$ref` are imported, running their import-time
  code, unless `allowed_modules` limits them
  ([Allowed modules](typed-configs.md#allowed-modules)); that is not a sandbox.
- Resolvers run, including `oc.env`, which reads any environment variable.
  `load_config` itself resolves `~import` paths and `$base` and `$defaults` values.
  Call `OmegaConf.clear_resolver("oc.env")` before loading if you do not need it.
- Every schema's `default_factory` runs during validation.
- `~import` reads any file the process can read, unless `import_root` is set
  ([Imports](assembly.md#imports)). `keep_targets=False` does not make loading safe.
- Overrides carry the same trust as files: they can set `$class`, `$ref` and
  `${oc.env:...}`.
- The command line puts the working directory first on `sys.path`, so a module
  there can shadow a `$class` target.
- Reading a special file, such as a FIFO, blocks.
- `~import` fan-out can grow exponentially (every import is a deep copy), and a
  long `$base` chain costs time quadratic in its length.
- Any string starting with `~import` is an import: YAML written from untrusted
  strings must not let them start with it.
- Error messages, and so CI logs, can contain scalar config values; mappings are
  described by their keys.

Resolved configs and built objects hold the real values of secrets read with
`${oc.env:...}`. Log `mask_secrets(config)`, and keep secrets out of arguments that
components save, such as hyperparameters in checkpoints.

### Masking secrets

`mask_secrets(config, *, keys=())` takes an unresolved config and returns it
resolved as plain dictionaries and lists, with secrets replaced by `***`:

1. **By key.** Keys are split into words at `_`, `-`, `.` and camelCase. A key is
   secret if its words contain `password`, `passwd`, `pass`, `passphrase`,
   `secret`, `token`, `credential`, `auth`, `bearer`, `cookie`, `dsn`, `webhook`,
   `apikey`, or the sequences `api key`, `private key`, `access key`, also plural.
   Whole words only: `pad_token` is secret, `tokenizer` is not. A secret key masks
   everything below it. `keys` adds words or space-separated sequences to the
   defaults.
2. **By environment variable.** A value whose unresolved text reads
   `${oc.env:NAME}` (also with spaces, or nested) is masked if `NAME` is secret by
   the same rule: `DB_PASSWORD` is, `APP_ENV` and `PWD` are not.
3. **By value.** Resolved strings masked by 1 or 2 with at least 8 characters are
   replaced by `***` inside every other string, longest first. Numbers and keys are
   never rewritten.

A masked value is resolved only to collect it for step 3, and stays masked if that
fails; a masked non-string becomes the string `***`. Missing values print as `???`.
Other resolution errors raise `ConfigValidationError`.

Not masked: secrets under keys that name no secret, secrets shorter than 8
characters used elsewhere, secrets used as keys, values from resolvers other than
`oc.env`, and built objects. A secret equal to a common word masks that word in
every other string.

## Resolvers

- OmegaConf's resolvers, such as `oc.env` (`${oc.env:NAME}`,
  `${oc.env:NAME,default}`), are always available; omegakit does not change them.
- omegakit's resolvers are opt-in, each imported from its own module;
  `omegakit.resolvers` exports nothing. Registration is global to OmegaConf, and an
  existing name raises unless `replace=True`.
- They are registered through the installed OmegaConf's API (`register_resolver` on
  2.4, `register_new_resolver` on 2.3), so neither version warns.
