# check

`omegakit check` loads config files and [validates](../../schemas/validation/index.md)
them, without building anything. Use it to look at an experiment before you launch
it, and to check every experiment file before each commit and in CI
([Checking experiments in CI](../../recipes/checking-experiments-in-ci/index.md)).

`--schema` names the class that the root of every file must build: here the root's
`$target` must name `project.Experiment` or a subclass. Files that are valid print
nothing:

```sh
omegakit check configs/experiments/*.yaml --schema project.Experiment
```

An invalid file prints one line, with the error that `validate` raised.
`--overrides` sets values in every file, so you can check a run with the values
you are about to give it:

```sh
omegakit check configs/experiments/mlp.yaml --overrides epochs=many --schema project.Experiment
```

```{code-block} text
:caption: Output

configs/experiments/mlp.yaml: ConfigSchemaError: The value does not match `Experiment`: Value 'many' of type 'str' could not be converted to Integer (at `epochs`)
```

## Files that others complete

A base file leaves values open for the experiments that extend it. `base.yaml`
sets `name: ???` and gives no model and no optimizer, so on its own it is invalid:

```sh
omegakit check configs/base.yaml --schema project.Experiment
```

```{code-block} text
:caption: Output

configs/base.yaml: ConfigSchemaError: `Experiment` requires `model`, `optimizer`. (at the root)
```

`--allow-missing` accepts what is missing and still checks every value the file
gives ([Validation](../../schemas/validation/index.md#files-that-are-incomplete-on-purpose)):

```sh
omegakit check configs/base.yaml --schema project.Experiment --allow-missing
```

## Rules

- `omegakit check CONFIG... [--overrides KEY=VALUE ...] [--schema QUALIFIED_NAME]
  [--allow-missing] [--include-root DIR]`.
- `check` runs `load_config` and `validate` on each file. `--include-root` is
  passed to `load_config` as `include_root`
  ([Includes](../../guide/includes/index.md#rules)), and `--schema` and
  `--allow-missing` to `validate` as `schema` and `allow_missing`
  ([Validation](../../schemas/validation/index.md#rules)). Without `--schema`, a
  root with `$target` is still checked against the fields or schema of its class.
- Every argument is a config file. `--overrides KEY=VALUE ...` applies to every
  file, in the order given, as the `overrides` of `load_config`. It takes the
  arguments up to the next option, so give the files before it, or end the
  overrides with `--`. Given more than once, the lists add up.
- It prints nothing for a valid file. For an invalid one it prints
  `<file>: <exception type>: <message>` to stderr, with the first line of the
  message, followed by the notes of the error, such as the node that an import
  failed at. Any exception, and a `SystemExit` raised by an imported module, marks
  that file invalid, and the other files are still checked. `KeyboardInterrupt`
  stops the command.
- It exits with 1 if any file is invalid.
- A `--schema` that cannot be imported or is not a class, and an `--include-root`
  that is not a directory, are usage errors: the command exits with 2 before any
  file is checked.
