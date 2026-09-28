# check

`omegakit check` loads config files and [validates](../../schemas/validation/index.md)
them, without building anything. Use it to look at an experiment before you launch
it, and to check every experiment file before each commit and in CI
([Checking experiments in CI](../../recipes/checking-experiments-in-ci/index.md)).

`--schema` names the class that the root of every file must match. Files that are
valid print nothing:

```sh
omegakit check configs/experiments/*.yaml --schema project.Experiment
```

An invalid file prints one line, with the error that `validate` raised. Overrides
after the files apply to every file, so you can check a run with the values you
are about to give it:

```sh
omegakit check configs/experiments/mlp.yaml epochs=many --schema project.Experiment
```

```{code-block} text
:caption: Output

configs/experiments/mlp.yaml: ConfigValidationError: Invalid config in `epochs` (Experiment): Value 'many' of type 'str' could not be converted to Integer
```

## Files that others complete

A base file leaves values open for the experiments that extend it, such as the
name, so on its own it is invalid:

```sh
omegakit check configs/base.yaml --schema project.Experiment
```

```{code-block} text
:caption: Output

configs/base.yaml: ConfigValidationError: Cannot resolve `name`: Missing mandatory value: name
```

`--allow-missing` accepts what is missing and still checks every value the file
gives ([Missing values](../../guide/missing-values/index.md)):

```sh
omegakit check configs/base.yaml --schema project.Experiment --allow-missing
```

## Limiting what a file can reach

Checking a file imports the modules that its `$class` and `$ref` name. For a file
from someone else, `--allow-module` limits them to your own package and the parts
of PyTorch you use, and `--import-root` keeps every `~import` inside a directory
([Restricting imports](../../security/restricting-imports/index.md)):

```sh
omegakit check configs/experiments/mlp.yaml 'model.$class=subprocess.Popen' --schema project.Experiment --allow-module project --allow-module torch.nn --allow-module torch.optim --import-root configs
```

```{code-block} text
:caption: Output

configs/experiments/mlp.yaml: ConfigValidationError: `$class: subprocess.Popen` in `model` names a module that is not in `allowed_modules`.
```

## Rules

- `check` runs `load_config` and `validate` on each file. `--schema`,
  `--allow-missing`, `--allow-module` and `--import-root` are passed to them as
  `schema`, `allow_missing`, `allowed_modules` and `import_root`
  ([Validation](../../schemas/validation/index.md#rules)).
- It prints `<file>: <exception type>: <message>` for each invalid file and
  nothing for valid ones. Any exception, and a `SystemExit` raised by an imported
  module, marks that file invalid, and the other files are still checked.
  `KeyboardInterrupt` stops the command.
- It exits with 1 if any file is invalid
  ([Overview](../index.md#rules)).
