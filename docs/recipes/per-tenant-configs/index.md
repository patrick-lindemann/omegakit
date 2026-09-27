# Per-tenant configs

A service that runs once per customer needs the same config many times, with a few
values changed for each. Keep the differences in one file and apply each tenant's
entry as overrides to the shared config.

```{literalinclude} tenants.yaml
:language: yaml
:caption: tenants.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
```

```text
acme 8001 1 5 logs/acme
globex 8002 4 20 logs/globex
```

Each tenant gets its own `App`, built from `configs/app.yaml` with that tenant's
values on top and its name in `log_dir`. Overrides win over the config files and are
checked like them, so a misspelled key in `tenants.yaml` is reported for that
tenant. See [Overrides](../../configs/overrides/index.md).
