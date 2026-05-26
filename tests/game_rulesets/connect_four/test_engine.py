from random import Random

import pytest

from game_rulesets.connect_four import ConnectFourEngine, ConnectFourSettings
from game_rulesets.enums import GameResult


def test_legal_and_random_actions_are_accepted() -> None:
    engine = ConnectFourEngine()
    state = engine.initial_state()

    action_space = engine.legal_actions(state, "x")
    random_action = engine.random_action(state, "x", random=Random(1))

    assert action_space.exhaustive is True
    assert len(action_space.actions) == 7
    assert engine.apply_action(state, action_space.actions[0], "x").state["board"][5][0] == "x"
    assert engine.apply_action(state, random_action, "x").state


def test_applies_gravity_and_rejects_full_columns() -> None:
    engine = ConnectFourEngine()
    state = engine.initial_state()

    state = engine.apply_action(state, {"column": 0}, "x").state
    state = engine.apply_action(state, {"column": 0}, "o").state

    assert state["board"][5][0] == "x"
    assert state["board"][4][0] == "o"

    for player in ("x", "o", "x", "o"):
        state = engine.apply_action(state, {"column": 0}, player).state

    with pytest.raises(ValueError, match="Column is full"):
        engine.apply_action(state, {"column": 0}, "x")


def test_detects_vertical_wins() -> None:
    engine = ConnectFourEngine()
    state = engine.initial_state()

    moves = [
        ("x", 0),
        ("o", 1),
        ("x", 0),
        ("o", 1),
        ("x", 0),
        ("o", 1),
        ("x", 0),
    ]
    transition = None
    for player, column in moves:
        transition = engine.apply_action(state, {"column": column}, player)
        state = transition.state

    assert transition is not None
    assert transition.is_finished is True
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"


def test_detects_horizontal_and_diagonal_wins() -> None:
    engine = ConnectFourEngine()
    horizontal_state = engine.initial_state()
    for player, column in (
        ("x", 0),
        ("o", 0),
        ("x", 1),
        ("o", 1),
        ("x", 2),
        ("o", 2),
    ):
        horizontal_state = engine.apply_action(horizontal_state, {"column": column}, player).state
    transition = engine.apply_action(horizontal_state, {"column": 3}, "x")
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"

    diagonal_state = engine.initial_state()
    for player, column in (
        ("x", 0),
        ("o", 1),
        ("x", 1),
        ("o", 2),
        ("x", 2),
        ("o", 3),
        ("x", 2),
        ("o", 3),
        ("x", 4),
        ("o", 3),
    ):
        diagonal_state = engine.apply_action(diagonal_state, {"column": column}, player).state
    transition = engine.apply_action(diagonal_state, {"column": 3}, "x")
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"


def test_detects_draws_on_full_boards() -> None:
    engine = ConnectFourEngine()
    settings = ConnectFourSettings(rows=1, columns=2, win_length=3)
    state = engine.initial_state(settings)

    state = engine.apply_action(state, {"column": 0}, "x", settings).state
    transition = engine.apply_action(state, {"column": 1}, "o", settings)

    assert transition.result == GameResult.DRAW
    assert transition.winner_player is None
