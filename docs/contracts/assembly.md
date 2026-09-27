# Assembly

These pages are the normative description of the configuration language.

## Pipeline

`load_config` runs, in order:

1. Parse the file.
2. Replace `~import` values, depth-first; each imported file resolves its own
   imports first.
3. Merge `$base`, children before parents.
4. Apply `$defaults`, children before parents.
5. Merge the overrides.
6. Strip `$meta` (unless `keep_meta=True`), and `$class`, `$ref` and `$partial` if
   `keep_targets=False`.

Overrides arrive after assembly: an `~import`, `$base` or `$defaults` in an override
stays literal, and `$meta` or construction keys in an override are stripped like
any other.

## Precedence

Strongest first:

1. Overrides.
2. The node's own keys.
3. Later items of a list-valued `$base`.
4. Earlier items of a list-valued `$base`.

- `$defaults` is weaker than the item it is applied to. Nested `$defaults`: the
  inner one wins, because it is applied first.
- `$defaults` reaches only the mapping-valued siblings in its own mapping; scalars,
  lists and `$` keys are untouched, and grandchildren only through the sibling's
  own keys.

## Resolution timing

Resolved during assembly: the path of an `~import` (including `${…}` in it), and the
values of `$base` and `$defaults`. Every other `${…}` resolves when it is read,
validated or built, against the assembled config; a relative one (`${.id}`) at the
node's final position. `instantiate` and `prepare` resolve a copy and never change
the config passed in.

- An `~import` path sees resolvers and the keys written in its own file, not keys
  from a `$base`, another file or overrides.
- A `${…}` value of `$base` or `$defaults` sees the referenced node with its own
  `$base` and `$defaults` merged. A node waits while its reference points at a node
  still holding `$base` (or `$defaults`) or at a key that does not exist yet, and
  ancestors of a waiting node wait too.
- A reference that never resolves, or references that form a cycle, raise
  `ConfigValidationError` naming the nodes.
- All bases are merged before any defaults, so a `$base` does not see keys its
  parent's `$defaults` add.

A `${…}` base is a copy taken when it is merged:

- It cannot refer to keys that an enclosing node's own `$base` brings in
  (`replica: {$base: ${db}}` in a file whose root has
  `$base: ~import common.yaml`, with `db` from `common.yaml`, raises).
- In a file used as another file's `$base`, it is merged there, before the other
  file's keys apply: replacing `db` later does not change the copy.
- Overrides do not reach the copy: `db.pool=9` leaves `replica.pool` unchanged.
- A relative reference (`${..db}`) to a sibling in the same file works wherever
  that file ends up.

## Missing values

`???` survives loading and can be filled by a node that uses its file as `$base`,
or by an override. If still missing, reading it raises OmegaConf's
`MissingMandatoryValue`, and validating or building a node that contains it raises
`ConfigValidationError` caused by it. Both name the full key.

## Imports

- Syntax: `~import <path>[#<node>]`; whitespace around `<path>` and `<node>` is
  ignored. Only a string value that starts with `~import` is an import.
- A relative `<path>` is relative to the importing file's directory.
- `<node>` is a dotted path from the imported file's root: keys in mappings,
  integer indices in lists, negative from the end (`#a.b.-1`). Empty means the
  whole file.
- An import can replace a mapping value or a list item. An imported file may hold
  a mapping or a list; the root file only a mapping. A single value (`hello`, `5`)
  is rejected everywhere; an empty file, `null` or `~` is an empty mapping.
- Every import is an independent copy. Each file is read once per `load_config`.
- A file that imports itself, directly or through others, is a cycle; the same file
  imported from two branches is not.
- `import_root=DIR` rejects an import outside `DIR`, after interpolations and
  symbolic links are resolved. A missing `DIR` raises `FileNotFoundError`, a file
  `NotADirectoryError`. The root file is not checked. The default allows any file.
- Raise `ConfigValidationError`: a cycle; more than one `#` (file names with `#`
  cannot be imported); a `<node>` that does not exist, walks through a scalar or an
  interpolation, or has a bad or out-of-range index.
