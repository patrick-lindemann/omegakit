# Editor schemas

`generate_json_schema` turns the dataclasses that describe a config into a JSON
Schema, so that YAML editors can check config files while you write them. The
schemas are the same as for [validation](validation.md): a root schema dataclass
for the whole file, and the schema of a `Configurable` class for its nodes.

## Generating JSON Schemas

Generate one schema for the root file and one for each fragment file whose content
is a single `Configurable` node:

```sh
omegakit json-schema editor_app.AppConfig -o app.schema.json
omegakit json-schema editor_app.Model -o model.schema.json
```

The import path must be importable from the current directory.
`python -m omegakit json-schema …` works the same. `omegakit.generate_json_schema`
returns the same schema as a dictionary.

To keep committed schemas current, run the same commands with `--check` in CI: it
writes nothing and exits with 1 when a file is out of date. See the
[command line](command-line.md).

## Connecting the editor

With the YAML extension for VS Code (by Red Hat, based on yaml-language-server),
name the schema in the first line of each file:

```{literalinclude} ../examples/editor/app.yaml
:language: yaml
```

```{literalinclude} ../examples/editor/model.yaml
:language: yaml
```

Alternatively, map files to schemas in the VS Code settings:

```json
{
  "yaml.schemas": {
    "./app.schema.json": "configs/app.yaml",
    "./model.schema.json": "configs/models/*.yaml"
  }
}
```

## What the schema checks

- Misspelled keys, and values of the wrong type, are errors.
- Interpolations (`${…}`), `???` and `~import` are accepted wherever a value is
  expected, and `$`-keys such as `$base`, `$defaults` and `$meta` are accepted in
  every mapping.
- Nothing is required, because a value may come from `$base`, `$defaults`, an
  import or an override. Missing values are reported by `validate` or `instantiate`.
- Enums accept member names, and `Literal` fields accept their values.
- A child node whose `$class` names a `Configurable` class with a dataclass schema
  is checked against that schema, for fields typed as that class. The `$class` must be the class's defining module
  and name; other spellings, such as re-exports, are accepted without checks.

## Editor behaviour

Checked in VS Code with the YAML extension by Red Hat, on the example files above:

- Errors appear for values of the wrong type (`batch_size: many`) and for misspelled
  keys, at the root (`sed: 1`) and inside a `$class` node (`widht: 8` under
  `encoder`).
- Interpolations (`${seed}`), `~import` values and `$` keys such as `$base` are
  accepted without errors.
- Completion offers the keys of the root schema, the values of `Literal` fields
  (`split: train`), and the fields of a node whose `$class` names a `Configurable`.
- Hover shows the field's type inside such a node.
- Enums accept member names and values (`kind: B`, `kind: beta`).
