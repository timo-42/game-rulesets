from pydantic import BaseModel

from game_rulesets.base import ActionSpace, PlayerId, RulesTransition
from game_rulesets.enums import GameResult


class PassAction(BaseModel):
    pass_turn: bool = True


class DummyThreePlayerEngine:
    key = "dummy-three-player"
    display_name = "Dummy Three Player"

    def initial_state(self, settings=None) -> dict:
        return {"turn": "a", "turns": 0}

    def legal_actions(self, state: dict, player_id: PlayerId, settings=None) -> ActionSpace:
        return ActionSpace(player_id=player_id, phase="turn", actions=[PassAction()])

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings=None,
    ) -> RulesTransition:
        order = ("a", "b", "c")
        next_index = (order.index(player_id) + 1) % len(order)
        turns = state["turns"] + 1
        if turns == 5:
            return RulesTransition(
                state={"turn": None, "turns": turns},
                active_player_ids=(),
                result=GameResult.WIN,
                winner_player_ids=("c",),
                turn_order=order,
            )
        return RulesTransition(
            state={"turn": order[next_index], "turns": turns},
            active_player_ids=(order[next_index],),
            turn_order=order,
        )


def test_contract_supports_more_than_two_players() -> None:
    engine = DummyThreePlayerEngine()
    state = engine.initial_state()

    transition = engine.apply_action(state, PassAction(), "a")

    assert transition.active_player_ids == ("b",)
    assert transition.next_player == "b"
    assert transition.turn_order == ("a", "b", "c")


def test_contract_supports_single_winner_from_many_players() -> None:
    engine = DummyThreePlayerEngine()
    state = {"turn": "c", "turns": 4}

    transition = engine.apply_action(state, PassAction(), "c")

    assert transition.is_finished is True
    assert transition.winner_player_ids == ("c",)
    assert transition.winner_player == "c"
