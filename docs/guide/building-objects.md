# Building objects

`instantiate` builds Python objects from a config node. `$class` calls a class or
function, `$ref` imports an object without calling it, and `$partial` defers a call.
`webapp` builds its whole application from the root file:

```{literalinclude} ../examples/guide/building-objects/main.py
:language: python
:caption: main.py
```

```text
SQLite Job
purged expired sessions
sent 'What happened this week'
sent 'Special offer'
1
`$class: subprocess.Popen` in `database` names a module that is not in `allowed_modules`.
```

## `$class`

`$class: webapp.App` names the class to build, and the node's other keys become its
arguments. Nested nodes with `$class`, in mappings and lists, are built first, so
`App` receives a built server, database and jobs. A class with a `from_config`
method, such as every `Configurable`, receives the arguments through it instead;
see [Typed configs](typed-configs.md). The node passed to `instantiate` must have
`$class`.

The second argument, `instantiate(config, App)`, gives the result its type for your
editor and type checker. It is not checked at runtime: `$class` decides what is
built.

## `$ref`

A `$ref` node is replaced by the object it names, without calling it. The `cleanup`
job's handler is the function itself:

```{literalinclude} ../examples/webapp/configs/jobs.yaml
:language: yaml
:caption: configs/jobs.yaml
:start-at: "cleanup:"
```

## `$partial` and `prepare`

`$partial: true` builds a `functools.partial` with the node's arguments, so the
`digest` handler is `send_digest` with its subject filled in, and a call can still
change the subject:

```{literalinclude} ../examples/webapp/configs/jobs.yaml
:language: yaml
:start-at: "digest:"
:end-before: "$meta:"
```

`prepare(node)` does the same for the node you pass: it checks the node and builds
its children, and gives you a partial for the node itself, to call later with more
arguments. Arguments passed to a partial win over the config's.

## `$meta`

`$meta` holds notes for people and tools, such as the `digest` job's owner. It is
never passed to a constructor or to `from_config`, and `load_config` removes it
unless you pass `keep_meta=True` ([Loading](loading.md)).

## Checking before building

`instantiate` and `prepare` check the node as [`validate`](validation.md) does
before they build anything, so a mistake raises `ConfigValidationError` before any
configured class is called. `allowed_modules=["webapp"]` limits `$class` and `$ref`
to your own package: the override above swapped in `subprocess.Popen`, and the
module was never imported. It limits what a config can name; it does not make an
untrusted config safe.

An exception raised by a constructor or `from_config` keeps its type and message,
and gets a note naming the node, such as `while instantiating jobs.digest
(webapp.jobs.Job)`. The rules are in the contracts under
[Instantiation](../contracts/instantiation.md#instantiation),
[References](../contracts/instantiation.md#references), [Partials](../contracts/instantiation.md#partials) and
[Metadata](../contracts/instantiation.md#metadata).
