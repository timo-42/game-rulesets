from random import Random
from typing import cast

from pydantic import BaseModel

from game_rulesets.base import (
    ActionSpace,
    GameObservation,
    PlayerId,
    RulesTransition,
    action_to_dict,
    next_player,
    open_information_observations,
    transition,
)
from game_rulesets.enums import GameResult
from game_rulesets.nine_mens_morris.actions import NineMensMorrisMove
from game_rulesets.nine_mens_morris.settings import (
    NineMensMorrisRuntimeSettings,
    NineMensMorrisSettings,
    nine_mens_morris_settings_from_snapshot,
    resolve_nine_mens_morris_settings,
)

POSITIONS = (
    "a1",
    "d1",
    "g1",
    "b2",
    "d2",
    "f2",
    "c3",
    "d3",
    "e3",
    "a4",
    "b4",
    "c4",
    "e4",
    "f4",
    "g4",
    "c5",
    "d5",
    "e5",
    "b6",
    "d6",
    "f6",
    "a7",
    "d7",
    "g7",
)
ADJACENT = {
    "a1": ("d1", "a4"),
    "d1": ("a1", "g1", "d2"),
    "g1": ("d1", "g4"),
    "b2": ("d2", "b4"),
    "d2": ("b2", "f2", "d1", "d3"),
    "f2": ("d2", "f4"),
    "c3": ("d3", "c4"),
    "d3": ("c3", "e3", "d2"),
    "e3": ("d3", "e4"),
    "a4": ("a1", "a7", "b4"),
    "b4": ("a4", "c4", "b2", "b6"),
    "c4": ("b4", "c3", "c5"),
    "e4": ("f4", "e3", "e5"),
    "f4": ("e4", "g4", "f2", "f6"),
    "g4": ("g1", "g7", "f4"),
    "c5": ("c4", "d5"),
    "d5": ("c5", "e5", "d6"),
    "e5": ("d5", "e4"),
    "b6": ("b4", "d6"),
    "d6": ("b6", "f6", "d5", "d7"),
    "f6": ("d6", "f4"),
    "a7": ("a4", "d7"),
    "d7": ("a7", "g7", "d6"),
    "g7": ("d7", "g4"),
}
MILLS = (
    ("a1", "d1", "g1"),
    ("b2", "d2", "f2"),
    ("c3", "d3", "e3"),
    ("a4", "b4", "c4"),
    ("e4", "f4", "g4"),
    ("c5", "d5", "e5"),
    ("b6", "d6", "f6"),
    ("a7", "d7", "g7"),
    ("a1", "a4", "a7"),
    ("b2", "b4", "b6"),
    ("c3", "c4", "c5"),
    ("d1", "d2", "d3"),
    ("d5", "d6", "d7"),
    ("e3", "e4", "e5"),
    ("f2", "f4", "f6"),
    ("g1", "g4", "g7"),
)


class NineMensMorrisEngine:
    key = "nine-mens-morris"
    display_name = "Nine Men's Morris"

    def resolve_settings(self) -> NineMensMorrisRuntimeSettings:
        return resolve_nine_mens_morris_settings()

    def settings_from_snapshot(self, snapshot: dict) -> NineMensMorrisRuntimeSettings:
        return nine_mens_morris_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
    ) -> dict:
        settings = resolve_nine_mens_morris_settings(settings)
        return {
            "board": {position: None for position in POSITIONS},
            "unplaced": {"x": settings.pieces_per_player, "o": settings.pieces_per_player},
        }

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
    ) -> NineMensMorrisMove:
        settings = resolve_nine_mens_morris_settings(settings)
        move = NineMensMorrisMove.model_validate(action_to_dict(action))
        _validated_next_state(state, move, player_id, settings)
        return move

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
    ) -> ActionSpace:
        settings = resolve_nine_mens_morris_settings(settings)
        actions = []
        for move in _candidate_moves(state, player_id, settings):
            try:
                _validated_next_state(state, move, player_id, settings)
            except ValueError:
                continue
            actions.append(move)
        return ActionSpace(
            player_id=player_id,
            phase=_phase(state, player_id, settings),
            actions=actions,
            total_count=len(actions),
        )

    def random_action(
        self,
        state: dict,
        player_id: PlayerId,
        settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> NineMensMorrisMove:
        random = random or Random()
        actions = list(self.legal_actions(state, player_id, settings).actions)
        if not actions:
            raise ValueError("No legal actions are available")
        return cast(NineMensMorrisMove, random.choice(actions))

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_move(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_nine_mens_morris_settings(settings)
        validated_move = self.validate_action(state, move, player, settings)
        next_state = _validated_next_state(state, validated_move, player, settings)
        opponent = next_player(player)
        if _placement_complete(next_state) and _piece_count(next_state, opponent) < 3:
            return transition(next_state, None, result=GameResult.WIN, winner_player_id=player)
        opponent_actions = self.legal_actions(next_state, opponent, settings).actions
        if _placement_complete(next_state) and not opponent_actions:
            return transition(next_state, None, result=GameResult.WIN, winner_player_id=player)
        return transition(next_state, opponent)

    def public_state(self, state: dict) -> dict:
        return state

    def observations_for_transition(
        self,
        *,
        event_payload: dict,
        state_before: dict | None,
        state_after: dict,
        settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return open_information_observations(
            event_payload=event_payload,
            state_before=state_before,
            state_after=state_after,
        )


def _validated_next_state(
    state: dict,
    move: NineMensMorrisMove,
    player: PlayerId,
    settings: NineMensMorrisRuntimeSettings,
) -> dict:
    board = state["board"].copy()
    unplaced = state["unplaced"].copy()
    before_mills = _player_mills(board, player)
    if move.action == "place":
        if unplaced[player] <= 0:
            raise ValueError("All pieces have already been placed")
        assert move.position is not None
        _validate_position(move.position)
        if board[move.position] is not None:
            raise ValueError("Position is already occupied")
        board[move.position] = player
        unplaced[player] -= 1
    else:
        if not _placement_complete(state):
            raise ValueError("Pieces must all be placed before movement begins")
        assert move.from_position is not None
        assert move.to_position is not None
        _validate_position(move.from_position)
        _validate_position(move.to_position)
        if board[move.from_position] != player:
            raise ValueError("from_position must contain the player's piece")
        if board[move.to_position] is not None:
            raise ValueError("to_position is already occupied")
        if (
            not _can_fly(state, player, settings)
            and move.to_position not in ADJACENT[move.from_position]
        ):
            raise ValueError("Pieces can only move to adjacent positions")
        board[move.from_position] = None
        board[move.to_position] = player

    next_state = {"board": board, "unplaced": unplaced}
    formed_mill = bool(_player_mills(board, player) - before_mills)
    if formed_mill:
        if move.remove_position is None:
            raise ValueError("A mill was formed; remove_position is required")
        _apply_capture(next_state, move.remove_position, next_player(player))
    elif move.remove_position is not None:
        raise ValueError("remove_position is only allowed after forming a mill")
    return next_state


def _apply_capture(state: dict, remove_position: str, opponent: PlayerId) -> None:
    _validate_position(remove_position)
    board = state["board"]
    if board[remove_position] != opponent:
        raise ValueError("remove_position must contain an opponent piece")
    capturable = _capturable_positions(board, opponent)
    if remove_position not in capturable:
        raise ValueError("Cannot capture a piece in a mill while other pieces are available")
    board[remove_position] = None


def _candidate_moves(
    state: dict,
    player: PlayerId,
    settings: NineMensMorrisRuntimeSettings,
) -> list[NineMensMorrisMove]:
    empty_positions = [position for position, owner in state["board"].items() if owner is None]
    remove_positions = [None] + _capturable_positions(state["board"], next_player(player))
    if state["unplaced"][player] > 0:
        return [
            NineMensMorrisMove(action="place", position=position, remove_position=remove_position)
            for position in empty_positions
            for remove_position in remove_positions
        ]
    moves: list[NineMensMorrisMove] = []
    for from_position, owner in state["board"].items():
        if owner != player:
            continue
        destinations = (
            empty_positions if _can_fly(state, player, settings) else ADJACENT[from_position]
        )
        for to_position in destinations:
            if state["board"][to_position] is not None:
                continue
            moves.extend(
                NineMensMorrisMove(
                    action="move",
                    from_position=from_position,
                    to_position=to_position,
                    remove_position=remove_position,
                )
                for remove_position in remove_positions
            )
    return moves


def _player_mills(board: dict[str, str | None], player: PlayerId) -> set[tuple[str, str, str]]:
    return {mill for mill in MILLS if all(board[position] == player for position in mill)}


def _capturable_positions(board: dict[str, str | None], player: PlayerId) -> list[str]:
    player_positions = [position for position, owner in board.items() if owner == player]
    outside_mills = [
        position for position in player_positions if not _position_in_mill(board, position, player)
    ]
    return outside_mills or player_positions


def _position_in_mill(board: dict[str, str | None], position: str, player: PlayerId) -> bool:
    return any(
        position in mill and all(board[mill_position] == player for mill_position in mill)
        for mill in MILLS
    )


def _phase(
    state: dict,
    player: PlayerId,
    settings: NineMensMorrisRuntimeSettings,
) -> str:
    if state["unplaced"][player] > 0:
        return "placement"
    return "flying" if _can_fly(state, player, settings) else "movement"


def _can_fly(
    state: dict,
    player: PlayerId,
    settings: NineMensMorrisRuntimeSettings,
) -> bool:
    return settings.flying_enabled and _piece_count(state, player) == 3


def _piece_count(state: dict, player: PlayerId) -> int:
    return sum(owner == player for owner in state["board"].values())


def _placement_complete(state: dict) -> bool:
    return bool(state["unplaced"]["x"] == 0 and state["unplaced"]["o"] == 0)


def _validate_position(position: str) -> None:
    if position not in POSITIONS:
        raise ValueError("Unknown board position")
