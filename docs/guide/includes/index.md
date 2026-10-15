# Includes

A value `~include <file>` is replaced by another YAML file, and
`~include <file>#<node>` by one node of it. One file can hold the model sizes that
experiments pick from:

```{literalinclude} models.yaml
:language: yaml
:caption: models.yaml
```

```{literalinclude} experiment.yaml
:language: yaml
:caption: experiment.yaml
```

```{literalinclude} main.py
:language: python
:caption: main.py
:end-before: import os
```

```{code-block} text
:caption: Output

config.model: {'hidden': 32, 'layers': 2}
```

`#small` selects the `small` node of the file, so `model` gets its keys and not a
`small:` key around them. Without `#`, the whole file is included.

## Keeping includes inside a directory

`include_root` limits includes to one directory. `experiments/large.yaml` includes
a file of its parent directory, which is outside `experiments`:

```{literalinclude} experiments/large.yaml
:language: yaml
:caption: experiments/large.yaml
```

```{literalinclude} main.py
:language: python
:start-at: import os
```

```{code-block} text
:caption: Output

config.model.hidden: 32
error: `.../models.yaml` is outside the include root `.../experiments`. (at `model` in `.../experiments/large.yaml`)
```

The error names the include that failed by its key and its file.

## Rules

- Syntax: `~include <file>` or `~include <file>#<node>`, as the whole value of a
  mapping key or a list item. Only a value that starts with `~include` and a space
  is an include; `a ~include b.yaml` and `~included` stay text.
- A relative `<file>` is relative to the directory of the including file. `${…}` in
  the value is resolved first, against the including file as it is written, as in
  `~include ${dir}/model.yaml`.
- `<node>` is selected with `OmegaConf.select`: `#a.b`, `#a.b[0]`, `#a.b.0` or
  `#a.b.-1`, following interpolations on the way. Without `#`, the whole file is
  included.
- A selected single value arrives resolved in its file, and a text arrives as it
  reads there: `\${x}` arrives as the text `${x}`, not as an interpolation. A
  selected mapping or list arrives as written, and its `${…}` resolve against the
  assembled config.
- An included file may hold a mapping or a list; the root file only a mapping.
  Every file loads as `OmegaConf.load` gives it ([Loading](../loading/index.md#rules)).
- Every include sees the files as they are written, not the result of another
  include, and every include is a copy of its own. Each file is read once per
  `load_config`.
- A file that includes itself, directly or through other files, is a cycle. The
  same file included from two places is not.
- `include_root=DIR` rejects every included file outside `DIR`, after `..` and
  symbolic links are resolved, with `IncludeRootError`, a `ConfigIncludeError`. The
  root file is not checked, and `load_config` does not check that `DIR` exists;
  `omegakit check` and `omegakit show` do. The default, `None`, allows any file.
- These raise `ConfigIncludeError`, with OmegaConf's error as its `__cause__` where
  there is one: a cycle, as in ``The includes form a cycle: `…/a.yaml` -> `…/b.yaml` ->
  `…/a.yaml`.``; a `${…}` in the value that cannot be resolved; a value that names no
  file or has more than one `#`, so a file whose name holds `#` cannot be included;
  a `<node>` that does not exist or holds `???`. An included file that does not
  exist, cannot be read or is no valid YAML raises the error of
  [Loading](../loading/index.md#rules), such as `ConfigFileNotFoundError`.
- Each error names the include that failed, as in ``(at `model` in `…/large.yaml`)``,
  and holds it in `full_key` and `file_path`. An include inside an included file
  adds a note for each include that led to it:
  ``from `~include models.yaml` at `model` in `…/experiment.yaml` ``.
