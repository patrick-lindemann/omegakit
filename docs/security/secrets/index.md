# Secrets

A resolved config holds the real value of every secret, and so do the objects built
from it. Log `mask_secrets(config)` instead:

```{literalinclude} main.py
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
`omegakit show` masks by key, and with `--resolve` also by environment variable and
by value ([Command line](../../guide/command-line/index.md#rules)). Keep secrets out of arguments that components
save, such as hyperparameters in checkpoints.

Masking is a safety net, not a guarantee. It cannot see a secret under a key that
names no secret, a secret shorter than 8 characters used inside another value, a
secret used as a key, a value from a resolver other than `oc.env`, or a built
object. A secret equal to a common word masks that word in every other string.

## Rules

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
