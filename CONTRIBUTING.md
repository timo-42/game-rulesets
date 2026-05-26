# Contributing

## Development

Install dependencies:

```bash
uv sync --extra dev
```

Run checks:

```bash
uv run ruff check src tests
uv run mypy src
uv run pytest
```

Build and validate distributions:

```bash
uv run python -m build
uv run twine check dist/*
```

## Test Layout

Tests mirror the package layout. For an engine at:

```text
src/game_rulesets/<ruleset>/engine.py
```

put tests in:

```text
tests/game_rulesets/<ruleset>/test_engine.py
```

Tests must be deterministic. If testing a random helper, pass an explicit seeded
`random.Random` instance.
