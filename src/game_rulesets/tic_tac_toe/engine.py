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
from game_rulesets.tic_tac_toe.actions import TicTacToeMove
from game_rulesets.tic_tac_toe.settings import (
    TicTacToeRuntimeSettings,
    TicTacToeSettings,
    resolve_tic_tac_toe_settings,
    tic_tac_toe_settings_from_snapshot,
)


class TicTacToeEngine:
    key = "tic-tac-toe"
    display_name = "Tic-tac-toe"

    def resolve_settings(self) -> TicTacToeRuntimeSettings:
        return resolve_tic_tac_toe_settings()

    def settings_from_snapshot(self, snapshot: dict) -> TicTacToeRuntimeSettings:
        return tic_tac_toe_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
    ) -> dict:
        settings = resolve_tic_tac_toe_settings(settings)
        return {"board": [[None for _ in range(settings.columns)] for _ in range(settings.rows)]}

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
    ) -> TicTacToeMove:
        settings = resolve_tic_tac_toe_settings(settings)
        move = TicTacToeMove.model_validate(action_to_dict(action))
        if move.row >= settings.rows or move.col >= settings.columns:
            raise ValueError("Move is outside the board")
        if state["board"][move.row][move.col] is not None:
            raise ValueError("Cell is already occupied")
        return move

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
    ) -> ActionSpace:
        settings = resolve_tic_tac_toe_settings(settings)
        actions = [
            TicTacToeMove(row=row, col=col)
            for row in range(settings.rows)
            for col in range(settings.columns)
            if state["board"][row][col] is None
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
        settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> TicTacToeMove:
        random = random or Random()
        actions = list(self.legal_actions(state, player_id, settings).actions)
        if not actions:
            raise ValueError("No legal actions are available")
        return cast(TicTacToeMove, random.choice(actions))

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_move(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_tic_tac_toe_settings(settings)
        validated_move = self.validate_action(state, move, player, settings)

        board = [line[:] for line in state["board"]]
        board[validated_move.row][validated_move.col] = player
        next_state = {"board": board}

        if _winner(board, player, settings):
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
        settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return open_information_observations(
            event_payload=event_payload,
            state_before=state_before,
            state_after=state_after,
        )


def _winner(
    board: list[list[str | None]],
    player: str,
    settings: TicTacToeRuntimeSettings,
) -> bool:
    return any(all(board[row][col] == player for row, col in line) for line in _win_lines(settings))


def _win_lines(settings: TicTacToeRuntimeSettings) -> list[list[tuple[int, int]]]:
    rows = [[(row, col) for col in range(settings.columns)] for row in range(settings.rows)]
    columns = [[(row, col) for row in range(settings.rows)] for col in range(settings.columns)]
    diagonals: list[list[tuple[int, int]]] = []
    if settings.rows == settings.columns:
        diagonals.append([(index, index) for index in range(settings.rows)])
        diagonals.append([(index, settings.columns - 1 - index) for index in range(settings.rows)])
    return rows + columns + diagonals
