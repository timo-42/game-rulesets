from random import Random
from typing import cast

from pydantic import BaseModel

from game_rulesets.axelrod_tournament.actions import AxelrodMove
from game_rulesets.axelrod_tournament.settings import (
    AxelrodTournamentRuntimeSettings,
    AxelrodTournamentSettings,
    axelrod_tournament_settings_from_snapshot,
    resolve_axelrod_tournament_settings,
)
from game_rulesets.base import (
    PUBLIC_VIEWER,
    ActionSpace,
    GameObservation,
    PlayerId,
    RulesTransition,
    action_to_dict,
    next_player,
    transition,
)
from game_rulesets.enums import GameResult

PLAYER_TO_VIEWER = {"x": "player_1", "o": "player_2"}
VIEWER_TO_PLAYER = {"player_1": "x", "player_2": "o"}


class AxelrodTournamentEngine:
    key = "axelrod-tournament"
    display_name = "Axelrod Tournament"

    def resolve_settings(self) -> AxelrodTournamentRuntimeSettings:
        return resolve_axelrod_tournament_settings()

    def settings_from_snapshot(self, snapshot: dict) -> AxelrodTournamentRuntimeSettings:
        return axelrod_tournament_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
    ) -> dict:
        settings = resolve_axelrod_tournament_settings(settings)
        return {
            "round": 1,
            "rounds": settings.rounds,
            "scores": {"x": 0, "o": 0},
            "history": [],
            "pending_move": None,
        }

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
    ) -> AxelrodMove:
        resolve_axelrod_tournament_settings(settings)
        _validate_expected_player(state, player_id)
        return AxelrodMove.model_validate(action_to_dict(action))

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
    ) -> ActionSpace:
        resolve_axelrod_tournament_settings(settings)
        _validate_expected_player(state, player_id)
        actions = [AxelrodMove(choice="cooperate"), AxelrodMove(choice="defect")]
        return ActionSpace(
            player_id=player_id,
            phase="choice",
            actions=actions,
            total_count=len(actions),
        )

    def random_action(
        self,
        state: dict,
        player_id: PlayerId,
        settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> AxelrodMove:
        random = random or Random()
        actions = list(self.legal_actions(state, player_id, settings).actions)
        return cast(AxelrodMove, random.choice(actions))

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_move(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_axelrod_tournament_settings(settings)
        validated_move = self.validate_action(state, move, player, settings)
        next_state = _copy_state(state)

        if next_state["pending_move"] is None:
            next_state["pending_move"] = {"player": player, "choice": validated_move.choice}
            return transition(next_state, next_player(player))

        pending_move = next_state["pending_move"]
        first_player = pending_move["player"]
        first_choice = pending_move["choice"]
        payoffs = _payoffs(first_choice, validated_move.choice, settings)

        round_record = {
            "round": next_state["round"],
            "choices": {
                first_player: first_choice,
                player: validated_move.choice,
            },
            "payoffs": {
                first_player: payoffs[0],
                player: payoffs[1],
            },
        }
        next_state["history"].append(round_record)
        next_state["scores"][first_player] += payoffs[0]
        next_state["scores"][player] += payoffs[1]
        next_state["pending_move"] = None

        if next_state["round"] >= settings.rounds:
            return _finished_transition(next_state)

        next_state["round"] += 1
        return transition(next_state, "x")

    def public_state(self, state: dict) -> dict:
        return _visible_state(state, PUBLIC_VIEWER)

    def observations_for_transition(
        self,
        *,
        event_payload: dict,
        state_before: dict | None,
        state_after: dict,
        settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return {
            viewer: GameObservation(
                visible_event_payload=_visible_event_payload(event_payload, viewer),
                visible_state_before=(
                    _visible_state(state_before, viewer) if state_before is not None else None
                ),
                visible_state_after=_visible_state(state_after, viewer),
            )
            for viewer in (PUBLIC_VIEWER, "player_1", "player_2")
        }


def _validate_expected_player(state: dict, player: PlayerId) -> None:
    if state["round"] > state["rounds"]:
        raise ValueError("The match is already finished")
    pending_move = state["pending_move"]
    expected_player = "x" if pending_move is None else next_player(pending_move["player"])
    if player != expected_player:
        raise ValueError(f"Expected player {expected_player}")


def _payoffs(
    first_choice: str,
    second_choice: str,
    settings: AxelrodTournamentRuntimeSettings,
) -> tuple[int, int]:
    if first_choice == "cooperate" and second_choice == "cooperate":
        return settings.mutual_cooperation_payoff, settings.mutual_cooperation_payoff
    if first_choice == "defect" and second_choice == "defect":
        return settings.punishment_payoff, settings.punishment_payoff
    if first_choice == "defect":
        return settings.temptation_payoff, settings.sucker_payoff
    return settings.sucker_payoff, settings.temptation_payoff


def _finished_transition(state: dict) -> RulesTransition:
    state["round"] += 1
    if state["scores"]["x"] > state["scores"]["o"]:
        return transition(state, None, result=GameResult.WIN, winner_player_id="x")
    if state["scores"]["o"] > state["scores"]["x"]:
        return transition(state, None, result=GameResult.WIN, winner_player_id="o")
    return transition(state, None, result=GameResult.DRAW)


def _copy_state(state: dict) -> dict:
    pending_move = state["pending_move"]
    return {
        "round": state["round"],
        "rounds": state["rounds"],
        "scores": state["scores"].copy(),
        "history": [
            {
                "round": entry["round"],
                "choices": entry["choices"].copy(),
                "payoffs": entry["payoffs"].copy(),
            }
            for entry in state["history"]
        ],
        "pending_move": pending_move.copy() if pending_move is not None else None,
    }


def _visible_state(state: dict, viewer: PlayerId) -> dict:
    pending_move = state["pending_move"]
    visible_pending = None
    if pending_move is not None:
        visible_pending = {"player": pending_move["player"]}
        if VIEWER_TO_PLAYER.get(viewer) == pending_move["player"]:
            visible_pending["choice"] = pending_move["choice"]
    return {
        "round": state["round"],
        "rounds": state["rounds"],
        "scores": state["scores"].copy(),
        "history": [
            {
                "round": entry["round"],
                "choices": entry["choices"].copy(),
                "payoffs": entry["payoffs"].copy(),
            }
            for entry in state["history"]
        ],
        "pending_move": visible_pending,
    }


def _visible_event_payload(payload: dict, viewer: PlayerId) -> dict:
    player = payload.get("player")
    if isinstance(player, str) and PLAYER_TO_VIEWER.get(player) == viewer:
        return payload
    if payload.get("action") == "move":
        return {"action": "move", "player": player}
    return payload
