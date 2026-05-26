from collections.abc import Sequence
from dataclasses import dataclass
from random import Random
from typing import Any, Protocol

from pydantic import BaseModel

from game_rulesets.enums import GameResult

type PlayerId = str
PUBLIC_VIEWER = "public"
PLAYER_X = "x"
PLAYER_O = "o"


class InvalidAction(ValueError):
    pass


class ActionSpaceTooLarge(RuntimeError):
    pass


@dataclass(frozen=True)
class RulesTransition:
    state: dict
    active_player_ids: tuple[PlayerId, ...]
    result: GameResult | None = None
    winner_player_ids: tuple[PlayerId, ...] = ()
    eliminated_player_ids: tuple[PlayerId, ...] = ()
    turn_order: tuple[PlayerId, ...] = ()

    @property
    def next_player(self) -> PlayerId | None:
        return self.active_player_ids[0] if self.active_player_ids else None

    @property
    def winner_player(self) -> PlayerId | None:
        return self.winner_player_ids[0] if len(self.winner_player_ids) == 1 else None

    @property
    def is_finished(self) -> bool:
        return self.result is not None


GameTransition = RulesTransition


@dataclass(frozen=True)
class GameObservation:
    visible_event_payload: dict
    visible_state_before: dict | None
    visible_state_after: dict


@dataclass(frozen=True)
class ActionSpace:
    player_id: PlayerId
    phase: str
    actions: Sequence[BaseModel]
    exhaustive: bool = True
    total_count: int | None = None
    reason: str | None = None


class RulesEngine(Protocol):
    key: str
    display_name: str

    def resolve_settings(self) -> BaseModel: ...

    def settings_from_snapshot(self, snapshot: dict) -> BaseModel: ...

    def initial_state(self, settings: Any | None = None) -> dict: ...

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: Any | None = None,
    ) -> RulesTransition: ...

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: Any | None = None,
    ) -> RulesTransition: ...

    def public_state(self, state: dict) -> dict: ...

    def observations_for_transition(
        self,
        *,
        event_payload: dict,
        state_before: dict | None,
        state_after: dict,
        settings: Any | None = None,
    ) -> dict[PlayerId, GameObservation]: ...


class LegalActionsProvider(Protocol):
    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: Any | None = None,
    ) -> ActionSpace: ...


class ActionValidator(Protocol):
    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: Any | None = None,
    ) -> BaseModel: ...


class RandomActionProvider(Protocol):
    def random_action(
        self,
        state: dict,
        player_id: PlayerId,
        settings: Any | None = None,
        random: Random | None = None,
    ) -> BaseModel: ...


class SampleActionsProvider(Protocol):
    def sample_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: Any | None = None,
        *,
        limit: int,
        random: Random | None = None,
    ) -> ActionSpace: ...


def next_player(player: PlayerId) -> PlayerId:
    return PLAYER_O if player == PLAYER_X else PLAYER_X


def transition(
    state: dict,
    next_player_id: PlayerId | None,
    *,
    result: GameResult | None = None,
    winner_player_id: PlayerId | None = None,
) -> RulesTransition:
    return RulesTransition(
        state=state,
        active_player_ids=() if next_player_id is None else (next_player_id,),
        result=result,
        winner_player_ids=() if winner_player_id is None else (winner_player_id,),
    )


def open_information_observations(
    *,
    event_payload: dict,
    state_before: dict | None,
    state_after: dict,
    viewers: Sequence[PlayerId] = (PUBLIC_VIEWER, "player_1", "player_2"),
) -> dict[PlayerId, GameObservation]:
    observation = GameObservation(
        visible_event_payload=event_payload,
        visible_state_before=state_before,
        visible_state_after=state_after,
    )
    return {viewer: observation for viewer in viewers}


def action_to_dict(action: BaseModel | dict) -> dict:
    if isinstance(action, BaseModel):
        return action.model_dump()
    return action
