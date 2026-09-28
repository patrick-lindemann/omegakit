# Loading

`load_config` reads a YAML file and returns an OmegaConf `DictConfig`, so
everything OmegaConf offers works on the result:

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-at: print(type(config)
```

```text
DictConfig 32 0.01
```

A file this plain loads as it is written. The following pages add what a file can
do while it loads: take parts from other files, extend a base, share defaults, and
take overrides.

## The order of assembly

`load_config` runs the features of the Guide in this order:

1. Every `~import` is replaced by the file or node it names ([Imports](../imports/index.md)).
2. Every `$base` is merged underneath its node ([Inheritance](../inheritance/index.md)).
3. Every `$defaults` is merged under its siblings ([Shared defaults](../shared-defaults/index.md)).
4. The overrides are merged on top ([Overrides](../overrides/index.md)).
5. `$meta` is removed, unless you pass `keep_meta=True`.

This order explains what works together. `$base: ~import base.yaml` works, because
the import is replaced before bases are merged. A `$defaults` that arrives through
a `$base` works, because defaults are applied after all bases. An override cannot
add an `~import`, a `$base` or a `$defaults`, because it arrives after assembly.

Only three things resolve while loading: `~import` paths, and the values of `$base`
and `$defaults`. Every other `${…}` stays as written until a value is read,
validated or built ([Interpolation](../interpolation/index.md)).

## Metadata

`$meta` holds notes for people and tools, such as the hypothesis of an experiment.
`load_config` removes it unless you ask for it, and `walk` visits every mapping of
a config, parents first, so a script can collect it:

```{literalinclude} annotated.yaml
:language: yaml
:caption: annotated.yaml
```

```{literalinclude} main.py
:language: python
:start-at: annotated.yaml
```

```text
False
A wider model fits the curve better.
```

`keep_targets=False` removes `$class`, `$ref` and `$partial`, which
[Building objects](../../objects/instantiation/index.md) uses. That leaves plain data
for code that builds nothing.

## Rules

**Pipeline.** `load_config` runs these steps in order:

1. Parse the root file. It must hold a mapping; a list raises `ConfigLoadError`.
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
  `ConfigLoadError` naming the nodes. [Inheritance](../inheritance/index.md#rules) and
  [Shared defaults](../shared-defaults/index.md#rules) say what each reference sees.

**Errors.** A missing root file raises `FileNotFoundError`. Every other problem in
a file's content raises `ConfigLoadError`, with the original error from
PyYAML, OmegaConf or the file system as its `__cause__`:

- A file that is not valid YAML, has duplicate keys or unknown tags, or is not
  UTF-8. The message names the file, the line and the column.
- A file that holds a single value, such as `hello` or `5`, instead of a mapping or
  a list. An empty file, `null` or `~` is an empty mapping.
- Any error while assembling: see [Imports](../imports/index.md#rules),
  [Inheritance](../inheritance/index.md#rules) and [Shared defaults](../shared-defaults/index.md#rules).
