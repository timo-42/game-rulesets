from random import Random

import pytest

from game_rulesets.chess import ChessEngine, ChessSettings
from game_rulesets.enums import GameResult


def test_legal_actions_and_illegal_moves_are_enforced() -> None:
    engine = ChessEngine()
    state = engine.initial_state()

    action_space = engine.legal_actions(state, "x")
    random_action = engine.random_action(state, "x", random=Random(1))

    assert action_space.exhaustive is True
    assert len(action_space.actions) == 20
    assert random_action.uci in {action.uci for action in action_space.actions}

    with pytest.raises(ValueError, match="Expected player x"):
        engine.apply_action(state, {"uci": "e7e5"}, "o")
    with pytest.raises(ValueError, match="not legal"):
        engine.apply_action(state, {"uci": "e2e5"}, "x")


def test_detects_checkmate() -> None:
    engine = ChessEngine()
    state = engine.initial_state()

    for player, uci in (
        ("x", "f2f3"),
        ("o", "e7e5"),
        ("x", "g2g4"),
    ):
        state = engine.apply_action(state, {"uci": uci}, player).state
    transition = engine.apply_action(state, {"uci": "d8h4"}, "o")

    assert transition.is_finished is True
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "o"


def test_supports_castling_promotion_and_en_passant() -> None:
    engine = ChessEngine()

    castle_settings = ChessSettings(starting_fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    transition = engine.apply_action(
        engine.initial_state(castle_settings),
        {"uci": "e1g1"},
        "x",
        castle_settings,
    )
    assert transition.state["fen"].startswith("r3k2r/8/8/8/8/8/8/R4RK1")

    promotion_settings = ChessSettings(starting_fen="8/P7/8/8/8/8/8/k6K w - - 0 1")
    transition = engine.apply_action(
        engine.initial_state(promotion_settings),
        {"uci": "a7a8q"},
        "x",
        promotion_settings,
    )
    assert transition.state["fen"].startswith("Q7/8/8/8/8/8/8/k6K")

    en_passant_settings = ChessSettings(starting_fen="8/8/8/3pP3/8/8/8/k6K w - d6 0 1")
    transition = engine.apply_action(
        engine.initial_state(en_passant_settings),
        {"uci": "e5d6"},
        "x",
        en_passant_settings,
    )
    assert transition.state["fen"].startswith("8/8/3P4/8/8/8/8/k6K")


def test_detects_stalemate_and_insufficient_material_draws() -> None:
    engine = ChessEngine()
    stalemate_settings = ChessSettings(starting_fen="7k/5K2/6Q1/8/8/8/8/8 b - - 0 1")
    stalemate_state = engine.initial_state(stalemate_settings)
    action_space = engine.legal_actions(stalemate_state, "o", stalemate_settings)
    assert action_space.actions == []
    with pytest.raises(ValueError, match="No legal actions"):
        engine.random_action(stalemate_state, "o", stalemate_settings)

    insufficient_settings = ChessSettings(starting_fen="8/8/8/8/8/8/8/k6K w - - 0 1")
    transition = engine.apply_action(
        engine.initial_state(insufficient_settings),
        {"uci": "h1g1"},
        "x",
        insufficient_settings,
    )
    assert transition.result == GameResult.DRAW
