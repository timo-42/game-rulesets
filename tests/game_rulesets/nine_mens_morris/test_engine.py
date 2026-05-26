import pytest

from game_rulesets.enums import GameResult
from game_rulesets.nine_mens_morris import NineMensMorrisEngine, NineMensMorrisSettings


def test_places_pieces_and_requires_capture_after_mill() -> None:
    engine = NineMensMorrisEngine()
    state = engine.initial_state()

    for player, position in (
        ("x", "a1"),
        ("o", "b2"),
        ("x", "d1"),
        ("o", "d2"),
    ):
        state = engine.apply_action(
            state,
            {"action": "place", "position": position},
            player,
        ).state

    with pytest.raises(ValueError, match="remove_position is required"):
        engine.apply_action(state, {"action": "place", "position": "g1"}, "x")

    transition = engine.apply_action(
        state,
        {"action": "place", "position": "g1", "remove_position": "b2"},
        "x",
    )

    assert transition.state["board"]["g1"] == "x"
    assert transition.state["board"]["b2"] is None
    assert transition.state["unplaced"]["x"] == 6


def test_capture_prefers_pieces_outside_mills() -> None:
    engine = NineMensMorrisEngine()
    state = _morris_state(
        {
            "a1": "x",
            "d1": "x",
            "b2": "o",
            "d2": "o",
            "f2": "o",
            "a4": "o",
        },
        unplaced={"x": 7, "o": 5},
    )

    with pytest.raises(ValueError, match="Cannot capture a piece in a mill"):
        engine.apply_action(
            state,
            {"action": "place", "position": "g1", "remove_position": "b2"},
            "x",
        )

    transition = engine.apply_action(
        state,
        {"action": "place", "position": "g1", "remove_position": "a4"},
        "x",
    )
    assert transition.state["board"]["a4"] is None


def test_moves_adjacent_then_flies_with_three_pieces() -> None:
    engine = NineMensMorrisEngine()
    settings = NineMensMorrisSettings(flying_enabled=True)
    movement_state = _morris_state(
        {
            "a1": "x",
            "d1": "x",
            "g1": "x",
            "b2": "x",
            "d2": "o",
            "f2": "o",
            "c3": "o",
            "d3": "o",
        }
    )

    with pytest.raises(ValueError, match="adjacent"):
        engine.apply_action(
            movement_state,
            {"action": "move", "from_position": "a1", "to_position": "f6"},
            "x",
            settings,
        )

    transition = engine.apply_action(
        movement_state,
        {"action": "move", "from_position": "a1", "to_position": "a4"},
        "x",
        settings,
    )
    assert transition.state["board"]["a4"] == "x"
    assert transition.state["board"]["a1"] is None

    flying_state = _morris_state(
        {
            "a1": "x",
            "d1": "x",
            "g1": "x",
            "b2": "o",
            "d2": "o",
            "f2": "o",
        }
    )
    transition = engine.apply_action(
        flying_state,
        {"action": "move", "from_position": "a1", "to_position": "f6"},
        "x",
        settings,
    )
    assert transition.state["board"]["f6"] == "x"


def test_wins_by_capture_or_blocking_after_placement() -> None:
    engine = NineMensMorrisEngine()
    capture_win_state = _morris_state(
        {
            "a1": "x",
            "d1": "x",
            "b2": "o",
            "d2": "o",
            "g4": "x",
            "c3": "x",
        }
    )
    transition = engine.apply_action(
        capture_win_state,
        {"action": "move", "from_position": "g4", "to_position": "g1", "remove_position": "b2"},
        "x",
    )
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"

    no_flying = NineMensMorrisSettings(flying_enabled=False)
    blocked_state = _morris_state(
        {
            "a1": "o",
            "d1": "x",
            "a4": "x",
            "b2": "o",
            "d2": "x",
            "b4": "x",
            "g1": "o",
            "f4": "x",
        }
    )
    transition = engine.apply_action(
        blocked_state,
        {"action": "move", "from_position": "f4", "to_position": "g4"},
        "x",
        no_flying,
    )
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"


def _morris_state(
    pieces: dict[str, str],
    *,
    unplaced: dict[str, int] | None = None,
) -> dict:
    positions = (
        "a1",
        "d1",
        "g1",
        "b2",
        "d2",
        "f2",
        "c3",
        "d3",
        "e3",
        "a4",
        "b4",
        "c4",
        "e4",
        "f4",
        "g4",
        "c5",
        "d5",
        "e5",
        "b6",
        "d6",
        "f6",
        "a7",
        "d7",
        "g7",
    )
    return {
        "board": {position: pieces.get(position) for position in positions},
        "unplaced": unplaced or {"x": 0, "o": 0},
    }
