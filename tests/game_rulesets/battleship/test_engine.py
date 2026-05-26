from random import Random

import pytest

from game_rulesets.battleship import BattleshipEngine, BattleshipRuntimeSettings
from game_rulesets.enums import GameResult


def test_setup_sampling_and_shot_legal_actions_are_accepted() -> None:
    engine = BattleshipEngine()
    settings = BattleshipRuntimeSettings(
        rows=10,
        columns=10,
        ship_lengths=(5, 4, 3, 3, 2),
    )
    state = engine.initial_state(settings)

    setup_space = engine.sample_actions(state, "x", settings, limit=2, random=Random(1))
    assert setup_space.exhaustive is False
    setup_transition = engine.apply_action(state, setup_space.actions[0], "x", settings)

    state = engine.apply_action(setup_transition.state, _fleet_o(), "o", settings).state
    shot_space = engine.legal_actions(state, "x", settings)

    assert shot_space.exhaustive is True
    assert len(shot_space.actions) == 100
    assert engine.apply_action(state, shot_space.actions[0], "x", settings).state


def test_rejects_repeated_shot() -> None:
    engine = BattleshipEngine()
    settings = engine.resolve_settings()
    state = engine.apply_action(engine.initial_state(settings), _fleet_x(), "x", settings).state
    state = engine.apply_action(state, _fleet_o(), "o", settings).state
    state = engine.apply_action(state, {"row": 0, "col": 0}, "x", settings).state

    with pytest.raises(ValueError, match="already targeted"):
        engine.apply_action(state, {"row": 0, "col": 0}, "x", settings)


def test_rejects_invalid_fleet_setup() -> None:
    engine = BattleshipEngine()
    settings = BattleshipRuntimeSettings(rows=4, columns=4, ship_lengths=(3, 2))
    state = engine.initial_state(settings)

    with pytest.raises(ValueError, match="configured ship lengths"):
        engine.apply_action(
            state,
            {
                "ships": [
                    {"length": 3, "row": 0, "col": 0, "orientation": "horizontal"},
                ]
            },
            "x",
            settings,
        )

    with pytest.raises(ValueError, match="may not overlap"):
        engine.apply_action(
            state,
            {
                "ships": [
                    {"length": 3, "row": 0, "col": 0, "orientation": "horizontal"},
                    {"length": 2, "row": 0, "col": 1, "orientation": "vertical"},
                ]
            },
            "x",
            settings,
        )


def test_rejects_out_of_bounds_ships_and_shots_before_battle() -> None:
    engine = BattleshipEngine()
    settings = BattleshipRuntimeSettings(rows=3, columns=3, ship_lengths=(2,))
    state = engine.initial_state(settings)

    with pytest.raises(ValueError, match="outside the board"):
        engine.apply_action(
            state,
            {"ships": [{"length": 2, "row": 0, "col": 2, "orientation": "horizontal"}]},
            "x",
            settings,
        )

    with pytest.raises(ValueError):
        engine.apply_action(state, {"row": 0, "col": 0}, "x", settings)


def test_setup_phase_and_visibility_rules() -> None:
    engine = BattleshipEngine()
    settings = BattleshipRuntimeSettings(rows=3, columns=3, ship_lengths=(2,))
    state = engine.initial_state(settings)
    transition = engine.apply_action(
        state,
        {"ships": [{"length": 2, "row": 0, "col": 0, "orientation": "horizontal"}]},
        "x",
        settings,
    )

    assert transition.active_player_ids == ("o",)
    with pytest.raises(ValueError, match="already submitted"):
        engine.apply_action(
            transition.state,
            {"ships": [{"length": 2, "row": 1, "col": 0, "orientation": "horizontal"}]},
            "x",
            settings,
        )

    public_state = engine.public_state(transition.state)
    assert public_state["fleets"]["x"]["ships"] == []
    observations = engine.observations_for_transition(
        event_payload={
            "action": "setup",
            "player": "x",
            "ships": [{"length": 2, "row": 0, "col": 0, "orientation": "horizontal"}],
            "ship_lengths": [2],
        },
        state_before=state,
        state_after=transition.state,
    )
    assert "ships" in observations["player_1"].visible_event_payload
    assert "ships" not in observations["player_2"].visible_event_payload


def test_wins_when_all_opponent_ships_are_sunk() -> None:
    engine = BattleshipEngine()
    settings = BattleshipRuntimeSettings(rows=3, columns=3, ship_lengths=(2,))
    state = engine.initial_state(settings)
    state = engine.apply_action(
        state,
        {"ships": [{"length": 2, "row": 0, "col": 0, "orientation": "horizontal"}]},
        "x",
        settings,
    ).state
    state = engine.apply_action(
        state,
        {"ships": [{"length": 2, "row": 1, "col": 0, "orientation": "horizontal"}]},
        "o",
        settings,
    ).state

    transition = engine.apply_action(state, {"row": 1, "col": 0}, "x", settings)
    assert transition.is_finished is False
    assert transition.state["fleets"]["x"]["shots"][-1] == {
        "row": 1,
        "col": 0,
        "hit": True,
        "sunk": False,
    }

    state = engine.apply_action(transition.state, {"row": 0, "col": 0}, "o", settings).state
    transition = engine.apply_action(state, {"row": 1, "col": 1}, "x", settings)

    assert transition.is_finished is True
    assert transition.result == GameResult.WIN
    assert transition.winner_player == "x"
    assert transition.state["fleets"]["x"]["shots"][-1]["sunk"] is True


def _fleet_x() -> dict:
    return {
        "ships": [
            {"length": 5, "row": 0, "col": 0, "orientation": "horizontal"},
            {"length": 4, "row": 1, "col": 0, "orientation": "horizontal"},
            {"length": 3, "row": 2, "col": 0, "orientation": "horizontal"},
            {"length": 3, "row": 3, "col": 0, "orientation": "horizontal"},
            {"length": 2, "row": 4, "col": 0, "orientation": "horizontal"},
        ]
    }


def _fleet_o() -> dict:
    return {
        "ships": [
            {"length": 5, "row": 0, "col": 0, "orientation": "vertical"},
            {"length": 4, "row": 0, "col": 1, "orientation": "vertical"},
            {"length": 3, "row": 0, "col": 2, "orientation": "vertical"},
            {"length": 3, "row": 0, "col": 3, "orientation": "vertical"},
            {"length": 2, "row": 0, "col": 4, "orientation": "vertical"},
        ]
    }
