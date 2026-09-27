# Assembly

## Pipeline

`load_config` assembles a file in this order:

1. Parse the YAML file.
2. Resolve `~import` depth-first. Each imported file resolves its own imports before
   it is inserted. No `$base` is merged during this step.
3. Merge `$base`, children before parents.
4. Apply `$defaults`, children before parents.
5. Merge the overrides.
6. Strip `$meta` (unless `keep_meta=True`) and the construction keys `$class`,
   `$ref` and `$partial` (if `keep_targets=False`).

Overrides cannot introduce `~import`, `$base` or `$defaults`: they arrive after
assembly, so these keys and values stay literal. `$meta` and construction keys
introduced by overrides are stripped like any other.

## Precedence

From strongest to weakest:

1. Overrides.
2. The node's own keys.
3. Later items of a list-valued `$base`.
4. Earlier items of a list-valued `$base`.

`$defaults` is weaker than the item it is applied to. Because `$defaults` is
applied children before parents, an inner `$defaults` has already been merged into
an item when an outer `$defaults` is merged underneath it, so the inner one wins.

`$defaults` applies only to the dict-valued siblings in its own mapping. Scalars,
lists and `$`-prefixed siblings are untouched, and grandchildren are reached only
through the merged sibling's own keys.

## Resolution timing

Only structural references are resolved during assembly:

- the path of an `~import`, including `${…}` inside it
- the value of `$base`
- the value of `$defaults`

An `~import` path is resolved against its own file as parsed: it sees resolvers
and the keys literally present in that file. It does not see keys contributed by a
`$base`, by another file, or by overrides.

A `$base` or `$defaults` value that is an interpolation (`$base: ${_common}`) sees
the referenced node with its own `$base` and `$defaults` already merged. Nodes are merged children before parents and
in dependency order:

- A node waits while its value refers to a node that still has an unmerged `$base`
  (or unapplied `$defaults`), or to a key that does not exist yet, such as a key
  that a later `$base` creates. It is merged as soon as the referenced node is.
- An ancestor of a waiting node waits too.
- References that can never be merged raise `ConfigValidationError`: a key that
  never appears (caused by the interpolation error), and nodes that refer to each
  other (`references form a cycle`), naming the nodes.
- All bases are merged before any defaults are applied, so a `$base` sees a node
  without the keys that its parent's `$defaults` add later.

A `${…}` base is a copy taken when it is merged, so it has three limits:

- It cannot refer to keys that an enclosing node's own `$base` brings in. With
  `$base: ~import common.yaml` at the root of a file, `replica: {$base: ${db}}`
  raises when `db` comes from `common.yaml`.
- Inside a file that another file uses as its `$base`, it is merged in that file,
  before the using file's own keys apply. A `replica` in `lib.yaml` that copies
  `lib.yaml`'s `db` keeps that copy when the using file replaces `db`.
- Overrides arrive after assembly, so an override of the referenced node does not
  reach the copy: `db.pool=9` leaves `replica.pool` as it was.

A relative reference (`${..db}`) finds a sibling wherever the file ends up, so a
`${…}` base placed next to the node it copies, in the file that defines both, copies
that file's value even when the file is itself used as a `$base` or imported.

Every other `${…}` stays an interpolation until it is accessed or instantiated, and
then resolves against the assembled config. This includes interpolations inside
imported files and inside `$base` and `$defaults` values. A relative interpolation
such as `${.id}` resolves at the node's final position.

`instantiate` and `prepare` resolve a copy. They never mutate the config passed in.

## Missing values

- A `???` value survives `load_config`.
- A consumer of the `$base` that carries it, or an override, can fill it.
- If it is still missing, accessing it raises OmegaConf's `MissingMandatoryValue`.
  Validating or instantiating any node that contains it raises
  `ConfigValidationError`, caused by `MissingMandatoryValue`. Both name the full
  key.

## Imports

- The syntax is `~import <path>[#<node>]`. Whitespace around `<path>` and around
  `<node>` is ignored.
- A relative path is resolved against the directory of the importing file. An
  absolute path is used as is.
- By default an import may read any file the process can read.
  `load_config(..., import_root=DIR)` rejects an import whose path, after
  interpolations and symbolic links are resolved, is not inside `DIR`. An
  `import_root` that does not exist raises `FileNotFoundError`, and one that is not
  a directory raises `NotADirectoryError`. The root file itself is not checked.
- `<node>` is a dot-separated path from the root of the imported file. A segment
  selects a key in a mapping or an integer index in a list (`#a.b.0`). A negative
  index counts from the end (`#a.b.-1`). An empty `<node>` selects the whole file.
- An import can replace a mapping value or a list item. The imported file may be a
  mapping or a list.
- A file that holds a single value (`hello`, `5`) raises `ConfigValidationError`,
  whether it is the root or imported. A list is allowed in an imported file, but not
  at the root of the file passed to `load_config`. An empty file, and a document that is only
  `null` or `~`, is an empty mapping.
- Cycles are detected per import chain: a file that imports itself, directly or
  through other files, raises `ConfigValidationError`. Importing the same file from
  two branches (a diamond) is not a cycle.
- Every import produces an independent copy. Changing one imported node never
  changes another import of the same file or node.
- Each imported file is read once per `load_config` call.
- A statement with more than one `#` raises `ConfigValidationError`. File names
  containing `#` cannot be imported.
- A `<node>` segment that walks through a scalar, a non-integer segment on a list,
  or an out-of-range index raises the same `ConfigValidationError` as a missing
  node. A path that goes through an interpolation in the imported file raises
  `ConfigValidationError` too; interpolations are not resolved while importing.
