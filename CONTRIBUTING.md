# Contributing

## Development

```sh
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
uv run pydoclint src
uv run pyright
uv run sphinx-build -W docs docs/_build
uv build
```

`uv run pytest` includes a test that builds the wheel and installs it into a fresh
environment; `-m "not distribution"` skips it. Tests of resolvers for an optional
library, such as Torch, skip when that library is absent; CI runs them in the
`test-resolvers` job, which installs the libraries.

To preview the documentation, build it and serve the result, then open
http://localhost:8000:

```sh
uv run sphinx-build docs docs/_build
uv run python -m http.server 8000 --directory docs/_build
```

Assembly relies on private OmegaConf node APIs. The supported OmegaConf range is
`>=2.3,<2.5`, and CI tests the lowest supported versions, the locked versions and
the newest OmegaConf pre-release in that range.

## Code

- Modules have plain names, as in OmegaConf. The public API is exactly
  `omegakit.__all__` plus the `omegakit.resolvers` subpackage; everything else is
  internal. Names used only in their own module get a leading underscore.
- Any change to the configuration language updates the Rules section of the
  affected guide page in the same commit.
- A bug fix comes with a test that fails without the fix.

## Commits

- One concern per commit. The message is one short line in the imperative, such as
  "Reject oversized tuples", with no body. A message that needs "and" describes two
  commits.
- Stage only the files of that change (`git add <paths>`).
- `CHANGELOG.md` changes only in the release commit.

## Dependencies

Dependabot proposes dependency and GitHub Actions updates weekly, and they are
reviewed and merged by hand. Actions are pinned to commit SHAs, so read the upstream
changes before merging a bump. The runtime bounds in `pyproject.toml` are changed by
hand, when the `test-omegaconf-next` job shows that a new version works.

## Releases

1. Bump the version with `uv version <version>`, add the `CHANGELOG.md` entry, and
   commit `pyproject.toml`, `uv.lock` and `CHANGELOG.md` together.
2. When a library compared in `docs/comparison.md` has had a major release, check
   the page against its documentation again and update its "Checked on" line.
3. On `main`, run `git pull`, then tag with `git tag -s v<version>` and push the
   tag.
4. The release workflow runs CI, checks that the tagged commit is on `main`, builds
   the distributions and, after the `pypi` environment is approved, publishes them
   with attestations.
