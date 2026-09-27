# Command line

Installing omegakit adds the `omegakit` command, also available as
`python -m omegakit`. Run it from the directory your configs import from, here
`webapp`'s:

```text
$ omegakit check configs/app.yaml --schema webapp.App --allow-module webapp
$ omegakit check configs/app.yaml server.workers=many --schema webapp.App
configs/app.yaml: ConfigValidationError: Invalid config in `server.workers` (ServerConfig): Value 'many' of type 'str' could not be converted to Integer
$ omegakit show configs/app.yaml --node server
$class: webapp.server.Server
host: 127.0.0.1
port: 8000
workers: 1
secret_key: '***'
$ omegakit show configs/app.yaml server.host=example.com --node cache.url --resolve
redis://example.com:6379
```

## `check`

`check` loads each file with the overrides and runs [`validate`](validation.md). It
prints one line per invalid file and nothing for valid ones, and exits with 1 if
any file is invalid.

- `--schema IMPORT_PATH` names the class every root must build, as `validate`'s
  `schema`.
- `--allow-missing` accepts `???` and other missing values, for files such as
  `base.yaml` that others complete:
  `omegakit check configs/base.yaml --schema webapp.App --allow-missing`.
- `--allow-module NAME`, repeatable, allows `$class` and `$ref` only from those
  modules and their submodules, as `validate`'s `allowed_modules`.
- `--import-root DIR` rejects an `~import` of a file outside `DIR`.

As a [pre-commit](https://pre-commit.com) hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: omegakit-check
        name: omegakit check
        entry: omegakit check --schema webapp.App --allow-module webapp
        language: system
        files: ^configs/app\.yaml$
```

`check` runs code from the files it checks: it imports the modules that `$class`
and `$ref` name and runs resolvers, including `oc.env`. Run it on trusted content
only:

- In CI, check your own branches. Do not run it in a `pull_request_target`
  workflow, which runs with your repository's secrets on a fork's files.
- Do not run pull requests from forks on self-hosted runners.
- Pass `--allow-module` for your own packages and `--import-root` for your config
  directory, to limit what a file can reach. They are limits, not a sandbox.

## `show`

`show` prints the assembled config: what imports, `$base`, `$defaults` and
overrides produced. Values stay as written unless you pass `--resolve`, so an
`${oc.env:...}` shows the variable's name, not its value.

- `--node KEY` prints one node, by the same dotted path as `~import file#node`, such
  as `jobs.digest` or `hosts.0`.
- `--resolve` resolves interpolations, only in the selected node, and prints
  missing values as `???`.
- Secrets are masked as by `mask_secrets`: by key name always, and with `--resolve`
  also by environment variable and inside other values. `--show-secrets` turns
  masking off.
- `--keep-meta` keeps `$meta` keys, and `--import-root DIR` works as for `check`.

## Arguments and exit codes

Config files and `key=value` overrides are given together. An argument that names
an existing file is a config file, even if it contains `=`; another argument is an
override if it has a `=` with no `/` before it. Overrides apply to every file.

The exit code is 0 on success, 1 when a config is invalid or cannot be loaded, and 2
for usage errors. The rules are in the contracts under
[Command line](../contracts/command-line.md#command-line).
