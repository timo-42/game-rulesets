# Release Process

This project uses PyPI trusted publishing where possible.

## One-time PyPI setup

1. Create the project on PyPI after the first successful upload, or reserve the name manually.
2. Add trusted publishers for this GitHub repository:
   - TestPyPI environment: `testpypi`
   - PyPI environment: `pypi`
3. Configure both publishers for `.github/workflows/publish.yml`.

## Release

1. Update `CHANGELOG.md`.
2. Commit and push the release changes.
3. For a TestPyPI build, run the `Publish` workflow manually from a branch and choose `testpypi`.
   The package version is generated from Git using `setuptools-scm` and is PEP 440 compliant.
4. For a PyPI release, create and push a tag for the final version:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

5. In GitHub Actions, run the `Publish` workflow manually from that tag and choose one target:
   - `pypi`
   - `both`

The publish workflow only requires a matching tag for `pypi` and `both`. The `testpypi`
target can run from a branch and uses the Git-derived development version.

## Local Checks

Run:

```bash
uv sync --extra dev
uv run ruff check src tests
uv run mypy src
uv run pytest
rm -rf dist/
uv run python -m build
uv run twine check dist/*
```

## Emergency Manual Upload

Use this only if trusted publishing is unavailable:

```bash
uv run twine upload --repository testpypi dist/*
uv run twine upload dist/*
```
