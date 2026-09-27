# Loading

`load_config` reads a YAML file and assembles it into an OmegaConf `DictConfig`.
The `webapp` root file holds two keys, and everything else arrives while loading:

```{literalinclude} ../examples/webapp/configs/app.yaml
:language: yaml
:caption: configs/app.yaml
```

```{literalinclude} ../examples/guide/loading/main.py
:language: python
:caption: main.py
:end-before: keep_meta
```

```text
9000
webapp.db.SQLite
```

The `$base` line pulled in `envs/dev.yaml`, which pulled in `base.yaml`, and the
override set the port last. Paths in `~import` are relative to the file that holds
them, not to the working directory, so the config loads from anywhere.

## The order of assembly

1. Every `~import` is replaced by the file or node it names ([Imports](imports.md)).
2. Every `$base` is merged underneath its node ([Base](base.md)).
3. Every `$defaults` is merged under its siblings ([Defaults](defaults.md)).
4. The overrides are merged on top
   ([Overrides and environment variables](overrides.md)).
5. `$meta` is removed, unless you pass `keep_meta=True`.

This order explains what works together. `$base: ~import base.yaml` works, because
the import is replaced before bases are merged. A `$defaults` that arrives through
a `$base` works, because defaults are applied after all bases. An override cannot
add an `~import`, a `$base` or a `$defaults`, because it arrives after assembly.

Only three things resolve while loading: `~import` paths, and the values of `$base`
and `$defaults`. Every other `${…}` stays as written until a value is read,
validated or built ([Interpolation and missing values](interpolation-and-missing.md)).

## Metadata and plain data

`$meta` holds notes for people and tools ([Building objects](building-objects.md)).
`load_config` removes it unless you ask for it. `walk` visits every mapping of a
config, parents first, so a script can collect it:

```{literalinclude} ../examples/guide/loading/main.py
:language: python
:start-at: keep_meta
```

```text
webapp.jobs.Job growth
```

`keep_targets=False` also removes `$class`, `$ref` and `$partial`. That leaves
plain data for code that builds nothing.

## Rules

**Pipeline.** `load_config` runs these steps in order:

1. Parse the root file. It must hold a mapping.
2. Replace `~import` values, depth-first. Each imported file resolves its own
   imports first.
3. Merge every `$base` underneath its node, children before parents.
4. Apply every `$defaults` to its siblings, children before parents.
5. Merge the overrides.
6. Strip `$meta`, unless `keep_meta=True`, and `$class`, `$ref` and `$partial` if
   `keep_targets=False`.

**Precedence**, strongest first:

1. Overrides.
2. The node's own keys.
3. Later items of a list-valued `$base`.
4. Earlier items of a list-valued `$base`.
5. `$defaults`, which is weaker than the item it is applied to.

**Resolution timing.**

- Resolved while assembling: the path of an `~import`, including any `${…}` in it,
  and the values of `$base` and `$defaults`.
- Every other `${…}` resolves when it is read, validated or built, against the
  assembled config. A relative one, such as `${.id}`, resolves at the node's final
  position.
- A `${…}` value of `$base` or `$defaults` is resolved while assembling. A node
  waits while its reference points at a node that still holds the same key, or at
  a key that does not exist yet, and the ancestors of a waiting node wait too. A
  reference that never resolves, and references that form a cycle, raise
  `ConfigValidationError` naming the nodes. [Base](base.md#rules) and
  [Defaults](defaults.md#rules) say what each reference sees.

**Errors.** A missing root file raises `FileNotFoundError`. Every other problem in
a file's content raises `ConfigValidationError`, with the original error as its
`__cause__`. The [Errors](../errors.md) table lists them.
