# Checking experiments in CI

Check every experiment file on every change, so that a broken config fails in CI
and not an hour into a run. Two steps cover it. `omegakit check` validates each
file and builds nothing, and a test builds each experiment. From the example
project's directory:

```sh
omegakit check configs/experiments/*.yaml --schema project.Experiment --include-root configs
```

`check` printed nothing, so every file is valid
([check](../../command-line/check/index.md)). `--include-root` rejects an include
of a file outside `configs` ([Includes](../../guide/includes/index.md#rules)). The
test loads each experiment with the same root and builds it, which also runs the
constructors and every `from_config`:

```{literalinclude} test_experiments.py
:language: python
:caption: test_experiments.py
```

In a GitHub Actions workflow, run both after installing your project:

```yaml
- run: omegakit check configs/experiments/*.yaml --schema project.Experiment --include-root configs
- run: pytest
```

Both run code from the configs they check, so set up the workflow as
[Trust model](../../security/trust-model/index.md#checking-configs-in-ci) describes.

To check every experiment file before each commit as well, run `check` as a
[pre-commit](https://pre-commit.com) hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: omegakit-check
        name: omegakit check
        entry: omegakit check --schema project.Experiment --include-root configs
        language: system
        files: ^configs/experiments/.*\.yaml$
```
