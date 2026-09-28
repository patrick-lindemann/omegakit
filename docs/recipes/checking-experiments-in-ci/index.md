# Checking experiments in CI

Check every experiment file on every change, so that a broken config fails in CI
and not an hour into a run. Two steps cover it. `omegakit check` validates each
file and builds nothing, and a test builds each experiment. From the example
project's directory:

```{code-block} text
:caption: Terminal

$ omegakit check configs/experiments/*.yaml --schema project.Experiment --allow-module project --allow-module torch.nn --allow-module torch.optim --import-root configs
```

`check` printed nothing, so every file is valid
([Command line](../../command-line/index.md)). The test builds each experiment with
the same limits, which also runs the constructors and every `from_config`:

```{literalinclude} test_experiments.py
:language: python
:caption: test_experiments.py
```

In a GitHub Actions workflow, run both after installing your project:

```yaml
- run: omegakit check configs/experiments/*.yaml --schema project.Experiment --allow-module project --allow-module torch.nn --allow-module torch.optim --import-root configs
- run: pytest
```

Both run code from the configs they check, so set up the workflow as
[Trust model](../../security/trust-model/index.md#checking-configs-in-ci) describes.
