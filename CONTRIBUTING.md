# Contributing

## Development

```sh
uv sync --all-groups
uv run pytest
uv run ruff check
uv run ruff format --check
uv run pydoclint src
uv run pyright
uv run sphinx-build -W docs docs/_build
uv build
```

`uv run pytest` includes a test that builds the wheel and installs it into a fresh
environment; `-m "not distribution"` skips it. The tests marked `docs` run the docs
examples and need the `docs` group, which includes PyTorch. The tests marked
`resolvers` test the optional resolvers and need the `resolvers` group. Each
optional resolver adds its library to that group. The tests of the library itself,
`-m "not docs and not resolvers"`, need neither. PyTorch comes from the CPU index.

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
  affected page in the same commit.
- A bug fix comes with a test that fails without the fix.

## Commits

- One concern per commit. The message is one short line in the imperative, such as
  "Reject oversized tuples", with no body. A message that needs "and" describes two
  commits.
- Stage only the files of that change (`git add <paths>`).
- A change that users can see adds its line to the `## [Unreleased]` section at the
  top of `CHANGELOG.md` in the same commit. Internal refactors, tests and CI changes
  get no line.

## Dependencies

Dependabot proposes dependency and GitHub Actions updates weekly against `develop`,
and they are reviewed and merged by hand. Actions are pinned to commit SHAs, so read the upstream
changes before merging a bump. The runtime bounds in `pyproject.toml` are changed by
hand, when the `test-omegaconf-next` job shows that a new version works.

## Branches

- Work happens on `develop`. A push there runs the quick CI jobs: lint, docs, the
  resolvers and the tests on Python 3.13.
- `main` holds released versions only. It moves only by merging a release pull
  request from `develop`, after the pull request has passed every CI job.

## Releases

1. **Release candidate.** When `develop` is ready, tag its last commit
   `v<version>-rc<N>`, starting at `rc1`, and push the tag. The release candidate
   workflow runs every CI job, builds the package as `<version>rc<N>` and, after the
   `testpypi` environment is approved, publishes it to TestPyPI. Try it from there:

   ```sh
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ omegakit==<version>rc<N>
   ```

   Fix a problem on `develop`, and tag the next candidate.
2. **Version commit.** On the candidate's commit, run `uv version <version>`. In
   `CHANGELOG.md`, rename `## [Unreleased]` to `## [<version>] - <date>`, check its
   lines against `git log v<previous>..HEAD`, and add the release link at the bottom.
   When a library compared in `docs/comparison/index.md` has had a major release,
   check the page against its documentation again and update its "Checked on"
   line. Commit `pyproject.toml`, `uv.lock` and `CHANGELOG.md` as
   "Prepare <version>", and push `develop`.
3. **Pull request.** Open a pull request from `develop` into `main`, titled
   "Release <version>". It runs every CI job on the result of the merge.
4. **Merge.** When it passes, click "Merge pull request". The repository allows
   only merge commits and names them after the pull request's title, so the merge
   commit is "Release <version>".
5. **Release.** The release workflow sees the new version on `main`. After the
   `pypi` environment is approved, it publishes the package to PyPI with
   attestations, then creates the tag `v<version>` on the merge commit and a GitHub
   release with the version's changelog section. It refuses a version without a
   release candidate, and does nothing for a version that is already released.
