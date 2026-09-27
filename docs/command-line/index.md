# Command line

Installing omegakit adds the `omegakit` command, also available as
`python -m omegakit`. Run it from the directory that your `$class` paths import
from, here `curvefit`'s:

```text
$ omegakit check configs/experiments/*.yaml --schema curvefit.Experiment --allow-module curvefit
$ omegakit check configs/experiments/poly3-adam.yaml trainer.epochs=many --schema curvefit.Experiment
configs/experiments/poly3-adam.yaml: ConfigValidationError: Invalid config in `trainer.epochs` (TrainerConfig): Value 'many' of type 'str' could not be converted to Integer
$ omegakit show configs/experiments/poly3-adam.yaml --node data.test
$class: curvefit.data.Synthetic
function:
  $ref: curvefit.data.sine
noise: 0.1
seed: 1234
'n': 200
$ omegakit show configs/experiments/poly3-adam.yaml seed=3 --node run_dir --resolve
runs/poly3-adam/seed3
```

## `check`

`check` loads each file with the overrides and runs
[`validate`](../schemas/validation/index.md). It prints one line per invalid file
and nothing for valid ones, and exits with 1 if any file is invalid. `--schema`
names the class every root must match, `--allow-missing` accepts `???` in files
such as `base.yaml` that others complete, `--allow-module` limits where `$class`
and `$ref` may point, and `--import-root` limits where `~import` may read.

To check every experiment file before a commit, run it as a
[pre-commit](https://pre-commit.com) hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: omegakit-check
        name: omegakit check
        entry: omegakit check --schema curvefit.Experiment --allow-module curvefit
        language: system
        files: ^configs/experiments/.*\.yaml$
```

`check` runs code from the files it checks, so run it on trusted content only.
[Trust model](../security/trust-model/index.md) says what runs and how to set up CI.

## `show`

`show` prints the assembled config: what imports, `$base`, `$defaults` and
overrides produced. The test split above got `$class`, `function` and `noise` from
`$defaults`, and `n` from its `$base`. Values stay as written unless you pass
`--resolve`, so an `${oc.env:...}` shows the variable's name, not its value.
`--resolve` shows the values a run will get; look at a run with it before you
launch it. `--node` prints one node, by the same dotted path as
`~import file#node`. Secrets are masked as by `mask_secrets`
([Masking secrets](../security/masking-secrets/index.md)).

## `json-schema`

`json-schema` writes the JSON Schema of a class for your editor; see
[Editor support](../schemas/editor-support/index.md).

## Rules

`omegakit` puts the working directory first on the import path, so `$class`,
`--schema` and `json-schema` paths resolve from there.

**Arguments.** `check` and `show` take config files and `key=value` overrides,
mixed in any order, all before or all after the options. Options between them are
a usage error. An argument that names an existing file is a config file, even with
`=` in it. Any other argument with `=` before the first
`/` is an override. Everything else is treated as a config file and fails to load.
Overrides apply to every file.

**Exit codes.** 0 on success. 1 when a config is invalid or cannot be loaded. 2 for
a usage error: no config file, an unknown option, a `--schema` or `json-schema`
path that cannot be imported, or an `--import-root` that is not a directory.

**`omegakit check CONFIG... [KEY=VALUE...] [--schema IMPORT_PATH] [--allow-missing]
[--allow-module NAME]... [--import-root DIR]`** validates each file
([Validation](../schemas/validation/index.md#rules)).

- `--schema` is passed as `validate`'s `schema`, `--allow-missing` as
  `allow_missing`, and each `--allow-module` adds an entry to `allowed_modules`
  ([Restricting imports](../security/restricting-imports/index.md#allowed-modules)). `--import-root` is passed to
  `load_config` as `import_root` ([Imports](../configs/imports/index.md#rules)).
- It prints `<file>: <exception type>: <message>` for each invalid file and
  nothing for valid ones. Any exception, and a `SystemExit` raised by an imported
  module, marks that file invalid, and the other files are still checked.
  `KeyboardInterrupt` stops the command.

**`omegakit show CONFIG [KEY=VALUE...] [--node KEY] [--resolve] [--keep-meta]
[--show-secrets] [--import-root DIR]`** prints the assembled config, or the node at
`KEY`, as YAML. A scalar prints as its value.

- `KEY` is a dotted path, walked as `~import file#node` is: `items.0.name`,
  `items.-1`. A node that does not exist, or a path through an interpolation
  without `--resolve`, exits with 1.
- Without `--resolve`, values print as written: `${…}`, `???`, `null`. With it,
  interpolations on the path are followed and only the selected node is resolved.
  Missing values print as `???`, and any other resolution error exits with 1 with
  one line.
- Secrets are masked as `mask_secrets` does. Keys are always masked. Environment
  variables and values are masked only with `--resolve`. The secrets are collected
  from the whole config, also with `--node`. `--show-secrets` turns masking off.
- `--keep-meta` keeps `$meta` keys.

**`omegakit json-schema IMPORT_PATH [-o FILE] [--check]`** prints or writes the
JSON Schema of the class at `IMPORT_PATH`. `--check` needs `-o`, writes nothing,
and exits with 1 if `FILE` is missing or differs from the generated schema,
compared as JSON.
