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
```

```{code-block} text
:caption: Output

type(config): DictConfig
config.model.hidden: 32
config.optimizer.lr: 0.01
```

A file this plain loads as it is written. The following pages add what a file can
do while it loads: [include other files](../includes/index.md),
[extend a base](../inheritance/index.md), [share defaults](../defaults/index.md)
and [take overrides](../overrides/index.md). `load_config` applies them in the order
under Rules, and that order explains what works together:

- `$base: ~include base.yaml` works, because the include is replaced before bases
  are merged.
- An `$each` that arrives through a `$base` works, because `$each` is applied after
  every `$base`.
- An override cannot add an `~include`, a `$base` or an `$each`, because it arrives
  after them.

## Rules

**Arguments.** `load_config(file_path, overrides=None, keep_meta=False,
include_root=None)`. `file_path` is a `Path` or a `str`, and every argument may be
given by position.

**Order.** `load_config` runs these steps:

1. Read the file. Its root must be a mapping.
2. Replace every `~include` ([Includes](../includes/index.md)).
3. Merge every `$base` under its node ([Inheritance](../inheritance/index.md)).
4. Merge every `$each` under the mappings beside it
   ([Defaults](../defaults/index.md)).
5. Apply the overrides ([Overrides](../overrides/index.md)).
6. Remove every `$meta` ([Metadata](../metadata/index.md)), unless
   `keep_meta=True`.

For an OmegaConf config created in memory, the same steps are available separately as
`resolve_includes`, `merge_bases`, `apply_each`, `apply_overrides` and
`remove_meta`. Call only the steps the config needs, in the order above. Each
returns a copy by default; pass `copy=False` to transform the config itself.

No step removes `$target`, `$symbol`, `$args` or `$partial`; they are read when
objects are built.

**Precedence**, strongest first:

1. Overrides.
2. The node's own keys.
3. Later items of a list-valued `$base`.
4. Earlier items of a list-valued `$base`.
5. `$each`, which is weaker than the mapping it is merged under.

**Resolution timing.**

- Resolved while loading: the `${…}` in an `~include` value, a single value that
  `~include file#node` selects, and the values of `$base` and `$each`.
- Every other `${…}` resolves when it is read, validated or built, against the
  loaded config. A relative one, such as `${.id}`, resolves at the node's final
  position.

**Saving.** The same files, overrides, environment variables and resolvers give
the same config. `OmegaConf.save` of a config from `load_config` writes it
assembled and unresolved, and `load_config` of that file gives an equal config,
except where an override added an `~include`, a `$base` or an `$each`: these apply
when the saved file is loaded.

**Files.** A file loads as `OmegaConf.load` gives it: a single string such as
`hello` is the mapping `{hello: null}`, and an empty file, `null` or `~` an empty
mapping.

**Errors.** Every error of omegakit that `load_config` raises is a
`ConfigLoadError`. Reading a file raises:

- `ConfigFileNotFoundError`, also a `FileNotFoundError`, for a file that does not
  exist.
- `ConfigFilePermissionError`, also a `PermissionError`, for a file that may not be
  read.
- `ConfigFileSyntaxError` for a file that is no valid YAML, has duplicate keys or
  unknown tags, is not UTF-8, or holds a single number or boolean, as in
  ``Cannot parse `…/experiment.yaml`: while constructing a mapping: found duplicate
  key seed (line 2, column 1)``. The line and column come only from a YAML error. A
  root file that holds a list raises it too.

`ConfigFileNotFoundError` and `ConfigFilePermissionError` carry the file in
`filename`, as the builtin errors do. Any other `OSError` while a file is read,
such as a failing disk, passes through unchanged. Each later step raises its own
error, named on its page.
