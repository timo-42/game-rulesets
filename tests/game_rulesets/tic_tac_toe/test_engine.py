from random import Random

import pytest

from game_rulesets.enums import GameResult
from game_rulesets.tic_tac_toe import TicTacToeEngine, TicTacToeSettings


def test_legal_and_random_actions_are_accepted() -> None:
    engine = TicTacToeEngine()
    state = engine.initial_state()

    action_space = engine.legal_actions(state, "x")
    random_action = engine.random_action(state, "x", random=Random(1))

    assert action_space.exhaustive is True
    assert len(action_space.actions) == 9
    assert engine.apply_action(state, action_space.actions[0], "x").state["board"][0][0] == "x"
    assert engine.apply_action(state, random_action, "x").state


def test_detects_wins_and_rejects_occupied_cells() -> None:
    engine = TicTacToeEngine()
    state = engine.initial_state()

    transition = engine.apply_action(state, {"row": 0, "col": 0}, "x")
    with pytest.raises(ValueError, match="already occupied"):
        engine.apply_action(transition.state, {"row": 0, "col": 0}, "o")

    state = transition.state
    state = engine.apply_action(state, {"row": 1, "col": 0}, "o").state
    state = engine.apply_action(state, {"row": 0, "col": 1}, "x").state
    state = engine.apply_action(state, {"row": 1, "col": 1}, "o").state
    transition = engine.apply_action(state, {"row": 0, "col": 2}, "x")

    assert transition.is_finished is True
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"


def test_detects_column_and_diagonal_wins() -> None:
    engine = TicTacToeEngine()

    column_state = engine.initial_state()
    for player, move in (
        ("x", {"row": 0, "col": 2}),
        ("o", {"row": 0, "col": 0}),
        ("x", {"row": 1, "col": 2}),
        ("o", {"row": 0, "col": 1}),
    ):
        column_state = engine.apply_action(column_state, move, player).state
    transition = engine.apply_action(column_state, {"row": 2, "col": 2}, "x")
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"

    diagonal_state = engine.initial_state()
    for player, move in (
        ("x", {"row": 0, "col": 0}),
        ("o", {"row": 0, "col": 1}),
        ("x", {"row": 1, "col": 1}),
        ("o", {"row": 0, "col": 2}),
    ):
        diagonal_state = engine.apply_action(diagonal_state, move, player).state
    transition = engine.apply_action(diagonal_state, {"row": 2, "col": 2}, "x")
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"


def test_rejects_out_of_bounds_moves() -> None:
    engine = TicTacToeEngine()

    with pytest.raises(ValueError, match="outside the board"):
        engine.apply_action(engine.initial_state(), {"row": 3, "col": 0}, "x")


def test_detects_draws() -> None:
    engine = TicTacToeEngine()
    settings = TicTacToeSettings(rows=2, columns=3)
    state = engine.initial_state(settings)

    state = engine.apply_action(state, {"row": 0, "col": 0}, "x", settings).state
    state = engine.apply_action(state, {"row": 0, "col": 1}, "o", settings).state
    state = engine.apply_action(state, {"row": 0, "col": 2}, "x", settings).state
    state = engine.apply_action(state, {"row": 1, "col": 0}, "o", settings).state
    state = engine.apply_action(state, {"row": 1, "col": 1}, "x", settings).state
    transition = engine.apply_action(state, {"row": 1, "col": 2}, "o", settings)

    assert transition.is_finished is True
    assert transition.result == GameResult.DRAW
    assert transition.winner_player is None
