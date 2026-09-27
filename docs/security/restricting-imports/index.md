# Restricting imports

Two settings limit what a config can reach. They are limits, not a sandbox: a
config that passes them still runs code.

## Allowed modules

`validate`, `instantiate` and `prepare` take `allowed_modules`, and
`omegakit check` takes `--allow-module NAME`, repeatable. They limit which modules
`$class` and `$ref` may name. [Instantiation](../../objects/instantiation/index.md) shows
an override that is rejected.

- `None`, the default, allows every module, and `[]` none. Any iterable of module
  names works and is read once. A `str` raises `TypeError`.
- An entry allows that module and its submodules: `["webapp", "torch.optim"]`
  allows `webapp.db.Postgres` and `torch.optim.Adam`, but not `webapp_evil.X` or
  `torch.load`. An entry that names a class allows nothing. `$ref: math.pi` needs
  `"math"`.
- Every node the validation walk reaches is checked, including nodes under `Any`,
  `Callable`, `list` and `dict` fields. Before importing, the module part of the
  path is checked, so a module that is not allowed never runs; its parent packages
  are still imported. After importing, the object's `__module__` is checked, if it
  has one. The second check rejects a name that an allowed module imported from
  elsewhere, such as `pkgx.db.run` for `from subprocess import run`, and accepts
  re-exports within an allowed package.
- A failing path raises `ConfigValidationError` naming the path and the node.
- Allowing modules such as `builtins`, `importlib`, `os`, `subprocess`, `shutil`
  or `pickle` removes the restriction in practice, because each of them can import
  or run arbitrary code.
- Not covered: resolvers, the `schema` argument and `--schema`, `json-schema`
  paths, and `instantiate` calls inside your own `from_config`.

## Import root

By default an `~import` may read any file the process can read. `load_config`
takes `import_root`, and `omegakit check` and `omegakit show` take
`--import-root DIR`, to keep imports inside one directory. [Imports](../../configs/imports/index.md)
shows an example and lists the rules.
