# Walk

`walk(config)` yields every mapping node of a config, depth-first, parents before
children. Mappings inside lists are included; lists themselves are not yielded.

## Example

```{literalinclude} ../examples/walk/app.yaml
:language: yaml
:caption: app.yaml
```

```{literalinclude} ../examples/walk/main.py
:language: python
:caption: main.py
```

## Rules

- The yielded nodes are the config's own `DictConfig` nodes, so changes to them
  change the config.
- Interpolations are not resolved while walking.
- `CLASS_KEY` and the other key constants spell the special keys, so code does not
  repeat the strings.
