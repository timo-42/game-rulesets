# game-rulesets

Reusable, bot-friendly rules engines for turn-based games.

The package contains pure game rules only: typed actions, settings snapshots, state transitions,
legal action discovery, random/sample action helpers, and player/public observations. It does not
depend on FastAPI, SQLAlchemy, environment settings, or any hosting platform.

## Included Engines

- Axelrod Tournament
- Battleship
- Checkers
- Chess
- Connect Four
- Go
- Nine Men's Morris
- Tic-tac-toe

## Install

```bash
pip install game-rulesets
```

For local development:

```bash
uv sync --extra dev
```

## Example

```python
from game_rulesets.tic_tac_toe import TicTacToeEngine

engine = TicTacToeEngine()
state = engine.initial_state()
actions = engine.legal_actions(state, "x").actions
transition = engine.apply_action(state, actions[0], "x")

print(transition.state)
```

## Engine Contract

Each engine exposes the same basic workflow:

- `resolve_settings()` returns validated runtime settings.
- `settings_from_snapshot(snapshot)` restores settings from serialized data.
- `initial_state(settings)` creates a game state.
- `legal_actions(state, player_id, settings)` returns legal typed actions.
- `random_action(state, player_id, settings, random=...)` samples one legal action.
- `apply_action(state, action, player_id, settings)` returns a `RulesTransition`.
- `public_state(state)` returns a public view of the state.
- `observations_for_transition(...)` returns player/public observations.

Rules engines are intentionally storage- and transport-agnostic. The caller owns persistence,
matchmaking, clocks, authentication, and API shape.

## Development

```bash
uv run ruff check src tests
uv run mypy src
uv run pytest
```

Build and validate the package:

```bash
uv run python -m build
uv run twine check dist/*
```

## License

MIT
