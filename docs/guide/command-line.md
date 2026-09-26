# Command line

Installing omegakit adds the `omegakit` command (also `python -m omegakit`). It runs
from the directory whose modules your configs import, such as your project root.

| Command | What it does |
|---|---|
| `omegakit check CONFIG... [KEY=VALUE...]` | Load and validate files; imports the modules they name |
| `omegakit show CONFIG [KEY=VALUE...]` | Print a config as `load_config` assembles it |
| `omegakit json-schema IMPORT_PATH [-o FILE]` | Write a JSON Schema for YAML editors ([Editor schemas](editor-schemas.md)) |

## Example

```{literalinclude} ../examples/command-line/server.yaml
:language: yaml
:caption: server.yaml
```

```{literalinclude} ../examples/command-line/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/command-line/main.py
:language: python
:caption: main.py
```

In a terminal, the same calls are:

```sh
omegakit show app.yaml server.host=example.com --resolve
omegakit check app.yaml server.host=example.com
omegakit check server.yaml --allow-missing
```

## `check`

`check` loads each file with the overrides and runs [`validate`](validation.md). It
prints one line per failing file and nothing for valid ones, and exits with 1 if any
file fails.

- `--schema IMPORT_PATH` names the class every root must match, as `validate`'s
  `schema`.
- `--allow-missing` accepts `???` and other missing values, for library files and
  fragments.
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
        entry: omegakit check --allow-module myapp
        language: system
        files: ^configs/.*\.yaml$
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
overrides produced.

- `--node KEY` prints one node, such as `--node training.model`.
- `--resolve` resolves interpolations, and prints missing values as `???`.
- `--keep-meta` keeps `$meta` keys.

## Arguments and exit codes

Config files and `key=value` overrides can come in any order. An argument that names
an existing file is a config file, even if it contains `=`. Other arguments with a
`=` are overrides, applied to every file.

The exit code is 0 on success, 1 when a config is invalid or cannot be loaded, and 2
for usage errors.
