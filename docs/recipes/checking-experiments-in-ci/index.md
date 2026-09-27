# Checking experiments in CI

Check every experiment file on every change, so that a broken config fails in CI
and not an hour into a run. Two steps cover it. `omegakit check` validates each
file and builds nothing, and a test builds each experiment. From `curvefit`'s
directory:

```text
$ omegakit check configs/experiments/*.yaml --schema curvefit.Experiment --allow-module curvefit --import-root configs
```

`check` prints nothing and exits with 0 when every file is valid
([Command line](../../command-line/index.md)). The test builds each experiment with
the same limits, which also runs the constructors and every `from_config`:

```{literalinclude} test_experiments.py
:language: python
:caption: test_experiments.py
```

In a GitHub Actions workflow, run both after installing your project:

```yaml
- run: omegakit check configs/experiments/*.yaml --schema curvefit.Experiment --allow-module curvefit --import-root configs
- run: pytest
```

Both run code from the configs they check. Run them on your own branches, not on
pull requests from forks with your secrets
([Trust model](../../security/trust-model/index.md#checking-configs-in-ci)).
