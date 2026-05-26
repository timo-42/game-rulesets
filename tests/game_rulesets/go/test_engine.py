import pytest

from game_rulesets.enums import GameResult
from game_rulesets.go import GoEngine, GoSettings


def test_captures_groups_and_rejects_suicide() -> None:
    engine = GoEngine()
    settings = GoSettings(board_size=3, komi=0.5)
    state = engine.initial_state(settings)

    for player, move in (
        ("x", {"row": 0, "col": 1}),
        ("o", {"row": 1, "col": 1}),
        ("x", {"row": 1, "col": 0}),
        ("o", {"move": "pass"}),
        ("x", {"row": 2, "col": 1}),
        ("o", {"move": "pass"}),
    ):
        state = engine.apply_action(state, move, player, settings).state

    transition = engine.apply_action(state, {"row": 1, "col": 2}, "x", settings)
    assert transition.state["board"][1][1] is None
    assert transition.state["captures"]["x"] == 1

    suicide_state = {
        "board": [
            [None, "x", None],
            ["x", None, "x"],
            [None, "x", None],
        ],
        "captures": {"x": 0, "o": 0},
        "consecutive_passes": 0,
        "previous_board": None,
    }
    with pytest.raises(ValueError, match="Suicide"):
        engine.apply_action(suicide_state, {"row": 1, "col": 1}, "o", settings)


def test_rejects_occupied_and_out_of_bounds_points() -> None:
    engine = GoEngine()
    settings = GoSettings(board_size=3, komi=0.5)
    state = engine.initial_state(settings)
    state = engine.apply_action(state, {"row": 0, "col": 0}, "x", settings).state

    with pytest.raises(ValueError, match="already occupied"):
        engine.apply_action(state, {"row": 0, "col": 0}, "o", settings)
    with pytest.raises(ValueError, match="outside the board"):
        engine.apply_action(state, {"row": 3, "col": 0}, "o", settings)


def test_legal_actions_exclude_suicide_but_include_pass() -> None:
    engine = GoEngine()
    settings = GoSettings(board_size=3, komi=0.5)
    state = {
        "board": [
            [None, "x", None],
            ["x", None, "x"],
            [None, "x", None],
        ],
        "captures": {"x": 0, "o": 0},
        "consecutive_passes": 0,
        "previous_board": None,
    }

    legal_actions = engine.legal_actions(state, "o", settings).actions

    assert any(action.move == "pass" for action in legal_actions)
    assert all(not (action.row == 1 and action.col == 1) for action in legal_actions)


def test_play_resets_consecutive_passes() -> None:
    engine = GoEngine()
    settings = GoSettings(board_size=3, komi=0.5)
    state = engine.initial_state(settings)

    state = engine.apply_action(state, {"move": "pass"}, "x", settings).state
    transition = engine.apply_action(state, {"row": 1, "col": 1}, "o", settings)

    assert transition.state["consecutive_passes"] == 0
    assert transition.active_player_ids == ("x",)


def test_ends_after_two_passes_and_scores_area() -> None:
    engine = GoEngine()
    settings = GoSettings(board_size=3, komi=0.5)
    state = {
        "board": [
            [None, "x", None],
            ["x", None, "x"],
            [None, "x", None],
        ],
        "captures": {"x": 0, "o": 0},
        "consecutive_passes": 0,
        "previous_board": None,
    }

    state = engine.apply_action(state, {"move": "pass"}, "x", settings).state
    transition = engine.apply_action(state, {"move": "pass"}, "o", settings)

    assert transition.is_finished is True
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"
    assert transition.state["scores"] == {"x": 9, "o": 0.5}


def test_rejects_simple_ko_recapture() -> None:
    engine = GoEngine()
    settings = GoSettings(board_size=3, komi=0.5)
    repeated_board = [
        ["x", None, "x"],
        [None, "x", None],
        [None, None, None],
    ]
    state = {
        "board": [
            ["x", "o", "x"],
            [None, None, None],
            [None, None, None],
        ],
        "captures": {"x": 0, "o": 0},
        "consecutive_passes": 0,
        "previous_board": repeated_board,
    }

    with pytest.raises(ValueError, match="simple ko"):
        engine.apply_action(state, {"row": 1, "col": 1}, "x", settings)
