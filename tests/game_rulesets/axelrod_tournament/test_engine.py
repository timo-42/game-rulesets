import pytest

from game_rulesets.axelrod_tournament import AxelrodTournamentEngine, AxelrodTournamentSettings
from game_rulesets.enums import GameResult


def test_scores_classic_prisoners_dilemma_rounds() -> None:
    engine = AxelrodTournamentEngine()
    settings = AxelrodTournamentSettings(rounds=2)
    state = engine.initial_state(settings)

    action_space = engine.legal_actions(state, "x", settings)
    assert action_space.exhaustive is True
    assert {action.choice for action in action_space.actions} == {"cooperate", "defect"}

    transition = engine.apply_action(state, {"choice": "cooperate"}, "x", settings)
    assert transition.active_player_ids == ("o",)
    public_state = engine.public_state(transition.state)
    assert public_state["pending_move"] == {"player": "x"}

    transition = engine.apply_action(transition.state, {"choice": "defect"}, "o", settings)
    assert transition.state["scores"] == {"x": 0, "o": 5}
    assert transition.state["history"][0]["choices"] == {"x": "cooperate", "o": "defect"}
    assert transition.active_player_ids == ("x",)

    transition = engine.apply_action(transition.state, {"choice": "defect"}, "x", settings)
    transition = engine.apply_action(transition.state, {"choice": "defect"}, "o", settings)

    assert transition.is_finished is True
    assert transition.winner_player == "o"
    assert transition.state["scores"] == {"x": 1, "o": 6}


def test_draws_when_scores_are_equal() -> None:
    engine = AxelrodTournamentEngine()
    settings = AxelrodTournamentSettings(rounds=1)
    state = engine.initial_state(settings)

    transition = engine.apply_action(state, {"choice": "cooperate"}, "x", settings)
    transition = engine.apply_action(transition.state, {"choice": "cooperate"}, "o", settings)

    assert transition.is_finished is True
    assert transition.result == GameResult.DRAW
    assert transition.state["scores"] == {"x": 3, "o": 3}


def test_rejects_out_of_order_players() -> None:
    engine = AxelrodTournamentEngine()
    state = engine.initial_state()

    with pytest.raises(ValueError, match="Expected player x"):
        engine.apply_action(state, {"choice": "cooperate"}, "o")


def test_rejects_moves_after_match_finished() -> None:
    engine = AxelrodTournamentEngine()
    settings = AxelrodTournamentSettings(rounds=1)
    state = engine.initial_state(settings)

    state = engine.apply_action(state, {"choice": "defect"}, "x", settings).state
    transition = engine.apply_action(state, {"choice": "cooperate"}, "o", settings)

    with pytest.raises(ValueError, match="already finished"):
        engine.apply_action(transition.state, {"choice": "defect"}, "x", settings)


def test_rejects_non_prisoners_dilemma_payoffs() -> None:
    with pytest.raises(ValueError, match="temptation > mutual cooperation"):
        AxelrodTournamentSettings(
            temptation_payoff=3,
            mutual_cooperation_payoff=5,
            punishment_payoff=1,
            sucker_payoff=0,
        )


def test_scores_all_payoff_cases() -> None:
    engine = AxelrodTournamentEngine()
    settings = AxelrodTournamentSettings(rounds=4)
    state = engine.initial_state(settings)

    for x_choice, o_choice in (
        ("cooperate", "cooperate"),
        ("cooperate", "defect"),
        ("defect", "cooperate"),
        ("defect", "defect"),
    ):
        state = engine.apply_action(state, {"choice": x_choice}, "x", settings).state
        transition = engine.apply_action(state, {"choice": o_choice}, "o", settings)
        state = transition.state

    assert state["history"][-4]["payoffs"] == {"x": 3, "o": 3}
    assert state["history"][-3]["payoffs"] == {"x": 0, "o": 5}
    assert state["history"][-2]["payoffs"] == {"x": 5, "o": 0}
    assert state["history"][-1]["payoffs"] == {"x": 1, "o": 1}
    assert state["scores"] == {"x": 9, "o": 9}
    assert transition.result == GameResult.DRAW
