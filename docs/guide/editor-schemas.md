# Editor schemas

The dataclasses that validate a config can also describe it to your YAML editor, as
a JSON Schema: the editor then completes keys and marks mistakes while you type.
From `webapp`'s directory:

```sh
omegakit json-schema webapp.App -o app.schema.json
```

The first line of each config file names the schema, which is how the YAML
extension for VS Code by Red Hat, and other editors that use yaml-language-server,
find it:

```{literalinclude} ../examples/webapp/configs/envs/prod.yaml
:language: yaml
:caption: configs/envs/prod.yaml
:lines: 1-4
```

The import path must be importable from the current directory, as for `$class`.
`generate_json_schema(App)` returns the same schema as a dictionary. For a file that
holds a single node, such as one job imported from its own file, generate the schema
of that node's class instead, such as `webapp.jobs.Job`.

Run the same command with `--check` in CI. It writes nothing, and exits with 1 when
the committed file no longer matches the classes.

## What the editor checks

Misspelled keys and values of the wrong type are errors, at the root and inside a
node whose `$class` names a `Configurable` with a dataclass schema. What the schema
cannot know is allowed everywhere: interpolations, `???`, `~import` and keys that
start with `$`. Nothing is required, because a value may still come from a `$base`,
`$defaults`, an import or an override; `validate` reports what is missing. Enums
accept their member names and values, and `Literal` fields their values.

A node is checked against its class's schema only when `$class` spells the class's
defining module and name, such as `webapp.server.Server`. A re-export such as
`webapp.Server` is accepted without checks.

Checked in VS Code with the Red Hat YAML extension, with omegakit 0.5.0: errors
appear for wrong types and misspelled keys, including inside a `$class` node;
interpolations, `~import` and `$` keys raise no errors; completion offers the root's
keys, `Literal` values and the fields of a `$class` node; hover shows a field's
type. The generated schema is described in the contracts under
[Editor schemas](../contracts.md#editor-schemas).
