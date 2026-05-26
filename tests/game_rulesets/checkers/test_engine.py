from random import Random

import pytest

from game_rulesets.checkers import CheckersEngine
from game_rulesets.enums import GameResult


def test_initial_setup_and_simple_moves() -> None:
    engine = CheckersEngine()
    state = engine.initial_state()

    action_space = engine.legal_actions(state, "x")
    random_action = engine.random_action(state, "x", random=Random(1))

    assert action_space.exhaustive is True
    assert len(action_space.actions) == 7
    assert sum(piece is not None for row in state["board"] for piece in row) == 24
    assert random_action.path in tuple(action.path for action in action_space.actions)

    transition = engine.apply_action(
        state,
        {"path": [{"row": 2, "col": 1}, {"row": 3, "col": 0}]},
        "x",
    )
    assert transition.state["board"][2][1] is None
    assert transition.state["board"][3][0] == {"player": "x", "king": False}


def test_enforces_mandatory_capture() -> None:
    engine = CheckersEngine()
    state = _checkers_state(
        {
            (2, 1): {"player": "x", "king": False},
            (3, 2): {"player": "o", "king": False},
            (5, 0): {"player": "o", "king": False},
        }
    )

    action_space = engine.legal_actions(state, "x")
    assert [_checkers_path(action) for action in action_space.actions] == [[(2, 1), (4, 3)]]

    with pytest.raises(ValueError, match="not legal"):
        engine.apply_action(state, {"path": [{"row": 2, "col": 1}, {"row": 3, "col": 0}]}, "x")

    transition = engine.apply_action(
        state,
        {"path": [{"row": 2, "col": 1}, {"row": 4, "col": 3}]},
        "x",
    )
    assert transition.state["board"][3][2] is None
    assert transition.state["board"][4][3] == {"player": "x", "king": False}


def test_supports_multi_jump_captures() -> None:
    engine = CheckersEngine()
    state = _checkers_state(
        {
            (2, 1): {"player": "x", "king": False},
            (3, 2): {"player": "o", "king": False},
            (5, 4): {"player": "o", "king": False},
            (7, 0): {"player": "o", "king": False},
        }
    )

    action_space = engine.legal_actions(state, "x")
    assert [_checkers_path(action) for action in action_space.actions] == [
        [(2, 1), (4, 3), (6, 5)]
    ]

    transition = engine.apply_action(
        state,
        {
            "path": [
                {"row": 2, "col": 1},
                {"row": 4, "col": 3},
                {"row": 6, "col": 5},
            ]
        },
        "x",
    )
    assert transition.state["board"][3][2] is None
    assert transition.state["board"][5][4] is None
    assert transition.state["board"][6][5] == {"player": "x", "king": False}


def test_promotes_men_and_kings_move_backward() -> None:
    engine = CheckersEngine()
    promotion_state = _checkers_state(
        {
            (6, 1): {"player": "x", "king": False},
            (0, 7): {"player": "o", "king": False},
        }
    )
    transition = engine.apply_action(
        promotion_state,
        {"path": [{"row": 6, "col": 1}, {"row": 7, "col": 0}]},
        "x",
    )
    assert transition.state["board"][7][0] == {"player": "x", "king": True}

    king_state = _checkers_state(
        {
            (4, 3): {"player": "x", "king": True},
            (3, 2): {"player": "o", "king": False},
            (0, 7): {"player": "o", "king": False},
        }
    )
    transition = engine.apply_action(
        king_state,
        {"path": [{"row": 4, "col": 3}, {"row": 2, "col": 1}]},
        "x",
    )
    assert transition.state["board"][3][2] is None
    assert transition.state["board"][2][1] == {"player": "x", "king": True}


def test_wins_when_opponent_has_no_pieces_or_moves() -> None:
    engine = CheckersEngine()
    no_pieces_state = _checkers_state(
        {
            (2, 1): {"player": "x", "king": False},
        }
    )
    transition = engine.apply_action(
        no_pieces_state,
        {"path": [{"row": 2, "col": 1}, {"row": 3, "col": 0}]},
        "x",
    )
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"

    blocked_state = _checkers_state(
        {
            (4, 1): {"player": "x", "king": False},
            (7, 0): {"player": "o", "king": False},
            (6, 1): {"player": "x", "king": False},
        }
    )
    transition = engine.apply_action(
        blocked_state,
        {"path": [{"row": 4, "col": 1}, {"row": 5, "col": 2}]},
        "x",
    )
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"


def _checkers_state(pieces: dict[tuple[int, int], dict]) -> dict:
    board = [[None for _ in range(8)] for _ in range(8)]
    for (row, col), piece in pieces.items():
        board[row][col] = piece.copy()
    return {"board": board}


def _checkers_path(move) -> list[tuple[int, int]]:
    return [(square.row, square.col) for square in move.path]
