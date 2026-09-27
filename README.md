# omegakit

YAML configs that import and extend each other, and build your Python objects. One
file per environment, one base they share, and an optional dataclass schema that
checks types and unknown keys before any configured object is built. A library on
OmegaConf: you call `load_config`, and it does not take over `main()`. Install it with
`pip install omegakit`, on Python 3.12 or newer.

```yaml
# base.yaml
server:
  $class: webapp.server.Server
  port: 8000
  secret_key: ???
database:
  $class: webapp.db.SQLite
  url: sqlite:///webapp.db
```

```yaml
# prod.yaml
$class: webapp.App
$base: ~import base.yaml
server:
  secret_key: ${oc.env:SECRET_KEY}
database:
  $class: webapp.db.Postgres
  url: postgres://db.internal/webapp
```

```python
from omegakit import instantiate, load_config
from webapp import App

app = instantiate(load_config("prod.yaml"), App)
```

`prod.yaml` took everything from `base.yaml` and replaced the database, and the
secret came from the environment. `App` is your class: `$class: webapp.App` at the
top of the file tells omegakit to build it, and the same key on the database node
chose Postgres. `webapp` is the example application of the
[documentation](https://omegakit.readthedocs.io).

## What you can do

- One config per environment, sharing a base:
  [Getting started](https://omegakit.readthedocs.io/en/latest/getting-started/#one-file-per-environment)
- Swap Postgres for SQLite in development and tests:
  [Swapping an implementation](https://omegakit.readthedocs.io/en/latest/recipes/swapping/)
- Check configs before anything runs, and get completion in your editor:
  [Validation](https://omegakit.readthedocs.io/en/latest/objects/validation/),
  [Editor support](https://omegakit.readthedocs.io/en/latest/tools/editor-support/)

Start with [Getting started](https://omegakit.readthedocs.io/en/latest/getting-started/),
or see how omegakit
[compares with Hydra and other libraries](https://omegakit.readthedocs.io/en/latest/comparison/).

## Trust

Configs import and call Python code: loading, validating and checking one imports
the modules it names and runs its resolvers. Load configs only from trusted sources,
and log them with `mask_secrets`. The
[Trust model](https://omegakit.readthedocs.io/en/latest/security/trust-model/) page lists what
runs.

omegakit supports OmegaConf 2.3 and 2.4. It builds on OmegaConf but is not affiliated
with or endorsed by the OmegaConf project.
[Contributing](https://github.com/patrick-lindemann/omegakit/blob/main/CONTRIBUTING.md).
