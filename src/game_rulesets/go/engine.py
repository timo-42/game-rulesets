from collections.abc import Iterable
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
from game_rulesets.go.actions import GoMove
from game_rulesets.go.settings import (
    GoRuntimeSettings,
    GoSettings,
    go_settings_from_snapshot,
    resolve_go_settings,
)


class GoEngine:
    key = "go"
    display_name = "Go"

    def resolve_settings(self) -> GoRuntimeSettings:
        return resolve_go_settings()

    def settings_from_snapshot(self, snapshot: dict) -> GoRuntimeSettings:
        return go_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: GoSettings | GoRuntimeSettings | None = None,
    ) -> dict:
        settings = resolve_go_settings(settings)
        return {
            "board": [
                [None for _ in range(settings.board_size)] for _ in range(settings.board_size)
            ],
            "captures": {"x": 0, "o": 0},
            "consecutive_passes": 0,
            "previous_board": None,
        }

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: GoSettings | GoRuntimeSettings | None = None,
    ) -> GoMove:
        settings = resolve_go_settings(settings)
        move = GoMove.model_validate(action_to_dict(action))
        if move.move == "pass":
            return move
        assert move.row is not None
        assert move.col is not None
        _simulate_play(state, move.row, move.col, player_id, settings)
        return move

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: GoSettings | GoRuntimeSettings | None = None,
    ) -> ActionSpace:
        settings = resolve_go_settings(settings)
        actions = [GoMove(move="pass")]
        for row in range(settings.board_size):
            for col in range(settings.board_size):
                try:
                    _simulate_play(state, row, col, player_id, settings)
                except ValueError:
                    continue
                actions.append(GoMove(row=row, col=col))
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
        settings: GoSettings | GoRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> GoMove:
        random = random or Random()
        actions = list(self.legal_actions(state, player_id, settings).actions)
        return cast(GoMove, random.choice(actions))

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: GoSettings | GoRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_move(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: GoSettings | GoRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_go_settings(settings)
        validated_move = self.validate_action(state, move, player, settings)
        if validated_move.move == "pass":
            next_state = _copy_state(state)
            next_state["previous_board"] = _copy_board(state["board"])
            next_state["consecutive_passes"] += 1
            if next_state["consecutive_passes"] >= 2:
                return _finished_transition(next_state, settings)
            return transition(next_state, next_player(player))

        assert validated_move.row is not None
        assert validated_move.col is not None
        board, captured_count = _simulate_play(
            state,
            validated_move.row,
            validated_move.col,
            player,
            settings,
        )
        next_state = {
            "board": board,
            "captures": state["captures"].copy(),
            "consecutive_passes": 0,
            "previous_board": _copy_board(state["board"]),
        }
        next_state["captures"][player] += captured_count
        return transition(next_state, next_player(player))

    def public_state(self, state: dict) -> dict:
        return state

    def observations_for_transition(
        self,
        *,
        event_payload: dict,
        state_before: dict | None,
        state_after: dict,
        settings: GoSettings | GoRuntimeSettings | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return open_information_observations(
            event_payload=event_payload,
            state_before=state_before,
            state_after=state_after,
        )


def _simulate_play(
    state: dict,
    row: int,
    col: int,
    player: PlayerId,
    settings: GoRuntimeSettings,
) -> tuple[list[list[str | None]], int]:
    if row >= settings.board_size or col >= settings.board_size:
        raise ValueError("Move is outside the board")
    if state["board"][row][col] is not None:
        raise ValueError("Point is already occupied")

    board = _copy_board(state["board"])
    board[row][col] = player
    opponent = next_player(player)
    captured_count = 0
    for neighbor in _neighbors(row, col, settings.board_size):
        neighbor_row, neighbor_col = neighbor
        if board[neighbor_row][neighbor_col] != opponent:
            continue
        group = _group(board, neighbor)
        if not _has_liberty(board, group, settings.board_size):
            captured_count += len(group)
            for group_row, group_col in group:
                board[group_row][group_col] = None

    own_group = _group(board, (row, col))
    if not _has_liberty(board, own_group, settings.board_size):
        raise ValueError("Suicide moves are illegal")
    if state["previous_board"] is not None and board == state["previous_board"]:
        raise ValueError("Move violates simple ko")
    return board, captured_count


def _finished_transition(state: dict, settings: GoRuntimeSettings) -> RulesTransition:
    scores = _area_scores(state["board"], settings)
    state["scores"] = scores
    if scores["x"] > scores["o"]:
        return transition(state, None, result=GameResult.WIN, winner_player_id="x")
    if scores["o"] > scores["x"]:
        return transition(state, None, result=GameResult.WIN, winner_player_id="o")
    return transition(state, None, result=GameResult.DRAW)


def _area_scores(board: list[list[str | None]], settings: GoRuntimeSettings) -> dict[str, float]:
    scores = {
        "x": sum(cell == "x" for row in board for cell in row),
        "o": float(sum(cell == "o" for row in board for cell in row)) + settings.komi,
    }
    seen: set[tuple[int, int]] = set()
    for row_index, row in enumerate(board):
        for col_index, cell in enumerate(row):
            point = (row_index, col_index)
            if cell is not None or point in seen:
                continue
            territory, borders = _empty_region(board, point, settings.board_size)
            seen.update(territory)
            if len(borders) == 1:
                owner = next(iter(borders))
                scores[owner] += len(territory)
    return scores


def _empty_region(
    board: list[list[str | None]],
    start: tuple[int, int],
    size: int,
) -> tuple[set[tuple[int, int]], set[str]]:
    region = {start}
    borders: set[str] = set()
    stack = [start]
    while stack:
        row, col = stack.pop()
        for neighbor in _neighbors(row, col, size):
            neighbor_row, neighbor_col = neighbor
            value = board[neighbor_row][neighbor_col]
            if value is None and neighbor not in region:
                region.add(neighbor)
                stack.append(neighbor)
            elif value is not None:
                borders.add(value)
    return region, borders


def _group(
    board: list[list[str | None]],
    start: tuple[int, int],
) -> set[tuple[int, int]]:
    color = board[start[0]][start[1]]
    group = {start}
    stack = [start]
    size = len(board)
    while stack:
        row, col = stack.pop()
        for neighbor in _neighbors(row, col, size):
            neighbor_row, neighbor_col = neighbor
            if board[neighbor_row][neighbor_col] == color and neighbor not in group:
                group.add(neighbor)
                stack.append(neighbor)
    return group


def _has_liberty(
    board: list[list[str | None]],
    group: Iterable[tuple[int, int]],
    size: int,
) -> bool:
    return any(
        board[neighbor_row][neighbor_col] is None
        for row, col in group
        for neighbor_row, neighbor_col in _neighbors(row, col, size)
    )


def _neighbors(row: int, col: int, size: int) -> tuple[tuple[int, int], ...]:
    return tuple(
        (neighbor_row, neighbor_col)
        for neighbor_row, neighbor_col in (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        )
        if 0 <= neighbor_row < size and 0 <= neighbor_col < size
    )


def _copy_state(state: dict) -> dict:
    return {
        "board": _copy_board(state["board"]),
        "captures": state["captures"].copy(),
        "consecutive_passes": state["consecutive_passes"],
        "previous_board": (
            _copy_board(state["previous_board"]) if state["previous_board"] is not None else None
        ),
    }


def _copy_board(board: list[list[str | None]]) -> list[list[str | None]]:
    return [row[:] for row in board]
