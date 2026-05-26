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
from game_rulesets.connect_four.actions import ConnectFourMove
from game_rulesets.connect_four.settings import (
    ConnectFourRuntimeSettings,
    ConnectFourSettings,
    connect_four_settings_from_snapshot,
    resolve_connect_four_settings,
)
from game_rulesets.enums import GameResult


class ConnectFourEngine:
    key = "connect-four"
    display_name = "Connect Four"

    def resolve_settings(self) -> ConnectFourRuntimeSettings:
        return resolve_connect_four_settings()

    def settings_from_snapshot(self, snapshot: dict) -> ConnectFourRuntimeSettings:
        return connect_four_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
    ) -> dict:
        settings = resolve_connect_four_settings(settings)
        return {"board": [[None for _ in range(settings.columns)] for _ in range(settings.rows)]}

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
    ) -> ConnectFourMove:
        settings = resolve_connect_four_settings(settings)
        move = ConnectFourMove.model_validate(action_to_dict(action))
        if move.column >= settings.columns:
            raise ValueError("Column is outside the board")
        if _drop_row(state["board"], move.column, settings) is None:
            raise ValueError("Column is full")
        return move

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
    ) -> ActionSpace:
        settings = resolve_connect_four_settings(settings)
        actions = [
            ConnectFourMove(column=column)
            for column in range(settings.columns)
            if _drop_row(state["board"], column, settings) is not None
        ]
        return ActionSpace(
            player_id=player_id,
            phase="move",
            actions=actions,
            total_count=len(actions),
        )

    def random_action(
        self,
        state: dict,
        player_id: PlayerId,
        settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> ConnectFourMove:
        random = random or Random()
        actions = list(self.legal_actions(state, player_id, settings).actions)
        if not actions:
            raise ValueError("No legal actions are available")
        return cast(ConnectFourMove, random.choice(actions))

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_move(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_connect_four_settings(settings)
        validated_move = self.validate_action(state, move, player, settings)

        board = [line[:] for line in state["board"]]
        row = _drop_row(board, validated_move.column, settings)
        if row is None:
            raise ValueError("Column is full")

        board[row][validated_move.column] = player
        next_state = {"board": board}

        if _winner(board, row, validated_move.column, player, settings):
            return transition(next_state, None, result=GameResult.WIN, winner_player_id=player)
        if all(cell is not None for line in board for cell in line):
            return transition(next_state, None, result=GameResult.DRAW)
        return transition(next_state, next_player(player))

    def public_state(self, state: dict) -> dict:
        return state

    def observations_for_transition(
        self,
        *,
        event_payload: dict,
        state_before: dict | None,
        state_after: dict,
        settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return open_information_observations(
            event_payload=event_payload,
            state_before=state_before,
            state_after=state_after,
        )


def _drop_row(
    board: list[list[str | None]],
    column: int,
    settings: ConnectFourRuntimeSettings,
) -> int | None:
    for row in range(settings.rows - 1, -1, -1):
        if board[row][column] is None:
            return row
    return None


def _winner(
    board: list[list[str | None]],
    row: int,
    column: int,
    player: str,
    settings: ConnectFourRuntimeSettings,
) -> bool:
    return any(
        1
        + _count(board, row, column, dr, dc, player, settings)
        + _count(board, row, column, -dr, -dc, player, settings)
        >= settings.win_length
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1))
    )


def _count(
    board: list[list[str | None]],
    row: int,
    column: int,
    dr: int,
    dc: int,
    player: str,
    settings: ConnectFourRuntimeSettings,
) -> int:
    total = 0
    row += dr
    column += dc
    while (
        0 <= row < settings.rows and 0 <= column < settings.columns and board[row][column] == player
    ):
        total += 1
        row += dr
        column += dc
    return total
