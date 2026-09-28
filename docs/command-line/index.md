# Command line

Installing omegakit adds the `omegakit` command, also available as
`python -m omegakit`. Run it from the directory that your `$class` paths import
from. The examples run in the example project's directory: its experiment files are
in `configs/experiments`, and the dataclass `project.Experiment` describes an
experiment, with `epochs: int`. Each command's `--help` lists its options.

## `check`

`check` loads config files and [validates](../schemas/validation/index.md) them,
without building anything. Valid files print nothing:

```sh
omegakit check configs/experiments/*.yaml --schema project.Experiment
```

An invalid file prints one line:

```sh
omegakit check configs/experiments/mlp.yaml epochs=many --schema project.Experiment
```

```{code-block} text
:caption: Output

configs/experiments/mlp.yaml: ConfigValidationError: Invalid config in `epochs` (Experiment): Value 'many' of type 'str' could not be converted to Integer
```

## `show`

`show` prints a config as `load_config` assembles it, so you see what imports,
`$base`, `$defaults` and overrides produced. With `--resolve` it prints the values a
run will get:

```sh
omegakit show configs/experiments/mlp.yaml --node data.test
```

```{code-block} text
:caption: Output

$class: project.SineWave
'n': 256
noise: 0.1
seed: 1234
```

```sh
omegakit show configs/experiments/mlp.yaml seed=3 --node run_dir --resolve
```

```{code-block} text
:caption: Output

runs/mlp/seed3
```

## `export-schema`

`export-schema` writes the JSON Schema of a class, for your editor
([Editor support](../schemas/editor-support/index.md)). With `--check` it writes
nothing, and fails when the file no longer matches the class:

```sh
omegakit export-schema project.Experiment -o experiment.schema.json --check
```

## Rules

`omegakit` puts the working directory first on the import path, so `$class`,
`--schema` and `export-schema` paths resolve from there.

**Arguments.** `check` and `show` take config files and `key=value` overrides,
mixed in any order, all before or all after the options. Options between them are
a usage error. An argument that names an existing file is a config file, even with
`=` in it. Any other argument with `=` before the first
`/` is an override. Everything else is treated as a config file and fails to load.
Overrides apply to every file.

**Exit codes.** 0 on success. 1 when a config is invalid or cannot be loaded. 2 for
a usage error: no config file, an unknown option, a `--schema` or `export-schema`
path that cannot be imported, or an `--import-root` that is not a directory.

**`check`** validates each file ([Validation](../schemas/validation/index.md#rules)),
with its options passed to `load_config` and `validate` under the same names.

- It prints `<file>: <exception type>: <message>` for each invalid file and
  nothing for valid ones. Any exception, and a `SystemExit` raised by an imported
  module, marks that file invalid, and the other files are still checked.
  `KeyboardInterrupt` stops the command.

**`show`** prints the assembled config, or the node at `--node`, as YAML. A scalar
prints as its value.

- `--node` takes a dotted path, walked as `~import file#node` is: `items.0.name`,
  `items.-1`. A node that does not exist, or a path through an interpolation
  without `--resolve`, exits with 1.
- Without `--resolve`, values print as written: `${…}`, `???`, `null`. With it,
  interpolations on the path are followed and only the selected node is resolved.
  Missing values print as `???`, and any other resolution error exits with 1 with
  one line.
- With `--resolve`, every value that `${secret:...}` gives is printed as `***`,
  also inside longer strings and also when it is read outside `--node`
  ([Secrets](../security/secrets/index.md#rules)).
- The command registers `${secret:...}` for `check` and `show`.

**`export-schema`** writes the JSON Schema of the class at its import path
([Editor support](../schemas/editor-support/index.md#rules)). `--check` needs `-o`,
and compares the file and the generated schema as JSON.
