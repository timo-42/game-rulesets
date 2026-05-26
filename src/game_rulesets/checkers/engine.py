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
from game_rulesets.checkers.actions import CheckersMove, CheckersSquare
from game_rulesets.checkers.settings import (
    CheckersRuntimeSettings,
    CheckersSettings,
    checkers_settings_from_snapshot,
    resolve_checkers_settings,
)
from game_rulesets.enums import GameResult

BOARD_SIZE = 8
START_ROWS = {"x": range(0, 3), "o": range(5, 8)}
FORWARD = {"x": 1, "o": -1}


class CheckersEngine:
    key = "checkers"
    display_name = "Checkers"

    def resolve_settings(self) -> CheckersRuntimeSettings:
        return resolve_checkers_settings()

    def settings_from_snapshot(self, snapshot: dict) -> CheckersRuntimeSettings:
        return checkers_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: CheckersSettings | CheckersRuntimeSettings | None = None,
    ) -> dict:
        resolve_checkers_settings(settings)
        board: list[list[dict | None]] = [
            [None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
        ]
        for player, rows in START_ROWS.items():
            for row in rows:
                for col in range(BOARD_SIZE):
                    if _is_dark_square(row, col):
                        board[row][col] = {"player": player, "king": False}
        return {"board": board}

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: CheckersSettings | CheckersRuntimeSettings | None = None,
    ) -> CheckersMove:
        settings = resolve_checkers_settings(settings)
        move = CheckersMove.model_validate(action_to_dict(action))
        legal_actions = self.legal_actions(state, player_id, settings).actions
        legal_paths = {_path_key(cast(CheckersMove, action).path) for action in legal_actions}
        if _path_key(move.path) not in legal_paths:
            raise ValueError("Move is not legal")
        return move

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: CheckersSettings | CheckersRuntimeSettings | None = None,
    ) -> ActionSpace:
        settings = resolve_checkers_settings(settings)
        captures = _capture_moves(state["board"], player_id)
        if captures and settings.mandatory_capture:
            actions = captures
        else:
            actions = captures + _simple_moves(state["board"], player_id)
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
        settings: CheckersSettings | CheckersRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> CheckersMove:
        random = random or Random()
        actions = list(self.legal_actions(state, player_id, settings).actions)
        if not actions:
            raise ValueError("No legal actions are available")
        return cast(CheckersMove, random.choice(actions))

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: CheckersSettings | CheckersRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_move(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: CheckersSettings | CheckersRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_checkers_settings(settings)
        validated_move = self.validate_action(state, move, player, settings)
        board = _copy_board(state["board"])
        path = [(square.row, square.col) for square in validated_move.path]
        start_row, start_col = path[0]
        piece = board[start_row][start_col]
        board[start_row][start_col] = None
        for (from_row, from_col), (to_row, to_col) in zip(path, path[1:], strict=False):
            if abs(to_row - from_row) == 2:
                board[(from_row + to_row) // 2][(from_col + to_col) // 2] = None
        end_row, end_col = path[-1]
        assert piece is not None
        if not piece["king"] and end_row == _king_row(player):
            piece = {**piece, "king": True}
        board[end_row][end_col] = piece

        next_state = {"board": board}
        opponent = next_player(player)
        if _piece_count(board, opponent) == 0:
            return transition(next_state, None, result=GameResult.WIN, winner_player_id=player)
        if not self.legal_actions(next_state, opponent, settings).actions:
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
        settings: CheckersSettings | CheckersRuntimeSettings | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return open_information_observations(
            event_payload=event_payload,
            state_before=state_before,
            state_after=state_after,
        )


def _simple_moves(board: list[list[dict | None]], player: PlayerId) -> list[CheckersMove]:
    moves = []
    for row, col, piece in _player_pieces(board, player):
        for dr, dc in _move_directions(player, piece["king"]):
            to_row = row + dr
            to_col = col + dc
            if _inside(to_row, to_col) and board[to_row][to_col] is None:
                moves.append(_move_from_path(((row, col), (to_row, to_col))))
    return moves


def _capture_moves(board: list[list[dict | None]], player: PlayerId) -> list[CheckersMove]:
    moves = []
    for row, col, piece in _player_pieces(board, player):
        moves.extend(
            _capture_paths(
                board,
                player,
                piece["king"],
                (row, col),
                ((row, col),),
            )
        )
    return [_move_from_path(path) for path in moves]


def _capture_paths(
    board: list[list[dict | None]],
    player: PlayerId,
    is_king: bool,
    position: tuple[int, int],
    path: tuple[tuple[int, int], ...],
) -> list[tuple[tuple[int, int], ...]]:
    row, col = position
    paths = []
    for dr, dc in _capture_directions(player, is_king):
        jumped_row = row + dr
        jumped_col = col + dc
        landing_row = row + 2 * dr
        landing_col = col + 2 * dc
        if not (_inside(jumped_row, jumped_col) and _inside(landing_row, landing_col)):
            continue
        jumped_piece = board[jumped_row][jumped_col]
        if (
            jumped_piece is None
            or jumped_piece["player"] == player
            or board[landing_row][landing_col] is not None
        ):
            continue
        next_board = _copy_board(board)
        moving_piece = next_board[row][col]
        next_board[row][col] = None
        next_board[jumped_row][jumped_col] = None
        next_board[landing_row][landing_col] = moving_piece
        if not is_king and landing_row == _king_row(player):
            paths.append(path + ((landing_row, landing_col),))
            continue
        continuations = _capture_paths(
            next_board,
            player,
            is_king,
            (landing_row, landing_col),
            path + ((landing_row, landing_col),),
        )
        paths.extend(continuations or [path + ((landing_row, landing_col),)])
    return paths


def _player_pieces(
    board: list[list[dict | None]],
    player: PlayerId,
) -> list[tuple[int, int, dict]]:
    return [
        (row, col, piece)
        for row, line in enumerate(board)
        for col, piece in enumerate(line)
        if piece is not None and piece["player"] == player
    ]


def _move_directions(player: PlayerId, is_king: bool) -> tuple[tuple[int, int], ...]:
    if is_king:
        return ((1, -1), (1, 1), (-1, -1), (-1, 1))
    return ((FORWARD[player], -1), (FORWARD[player], 1))


def _capture_directions(player: PlayerId, is_king: bool) -> tuple[tuple[int, int], ...]:
    return _move_directions(player, is_king)


def _move_from_path(path: tuple[tuple[int, int], ...]) -> CheckersMove:
    return CheckersMove(path=tuple(CheckersSquare(row=row, col=col) for row, col in path))


def _path_key(path: tuple[CheckersSquare, ...]) -> tuple[tuple[int, int], ...]:
    return tuple((square.row, square.col) for square in path)


def _copy_board(board: list[list[dict | None]]) -> list[list[dict | None]]:
    return [[piece.copy() if piece is not None else None for piece in row] for row in board]


def _piece_count(board: list[list[dict | None]], player: PlayerId) -> int:
    return sum(
        piece is not None and piece["player"] == player
        for row in board
        for piece in row
    )


def _king_row(player: PlayerId) -> int:
    return 7 if player == "x" else 0


def _inside(row: int, col: int) -> bool:
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def _is_dark_square(row: int, col: int) -> bool:
    return (row + col) % 2 == 1
