from random import Random
from typing import cast

import chess
from pydantic import BaseModel

from game_rulesets.base import (
    ActionSpace,
    GameObservation,
    PlayerId,
    RulesTransition,
    action_to_dict,
    open_information_observations,
    transition,
)
from game_rulesets.chess.actions import ChessMove
from game_rulesets.chess.settings import (
    ChessRuntimeSettings,
    ChessSettings,
    chess_settings_from_snapshot,
    resolve_chess_settings,
)
from game_rulesets.enums import GameResult


class ChessEngine:
    key = "chess"
    display_name = "Chess"

    def resolve_settings(self) -> ChessRuntimeSettings:
        return resolve_chess_settings()

    def settings_from_snapshot(self, snapshot: dict) -> ChessRuntimeSettings:
        return chess_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: ChessSettings | ChessRuntimeSettings | None = None,
    ) -> dict:
        settings = resolve_chess_settings(settings)
        board = chess.Board(settings.starting_fen)
        return _state_from_board(board)

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: ChessSettings | ChessRuntimeSettings | None = None,
    ) -> ChessMove:
        resolve_chess_settings(settings)
        move = ChessMove.model_validate(action_to_dict(action))
        board = _board_from_state(state)
        _validate_turn(board, player_id)
        try:
            chess_move = chess.Move.from_uci(move.uci)
        except ValueError as error:
            raise ValueError("Move must be valid UCI notation") from error
        if chess_move not in board.legal_moves:
            raise ValueError("Move is not legal")
        return move

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: ChessSettings | ChessRuntimeSettings | None = None,
    ) -> ActionSpace:
        resolve_chess_settings(settings)
        board = _board_from_state(state)
        _validate_turn(board, player_id)
        actions = [ChessMove(uci=move.uci()) for move in board.legal_moves]
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
        settings: ChessSettings | ChessRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> ChessMove:
        random = random or Random()
        actions = list(self.legal_actions(state, player_id, settings).actions)
        if not actions:
            raise ValueError("No legal actions are available")
        return cast(ChessMove, random.choice(actions))

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: ChessSettings | ChessRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_move(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: ChessSettings | ChessRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_chess_settings(settings)
        validated_move = self.validate_action(state, move, player, settings)
        board = _board_from_state(state)
        board.push(chess.Move.from_uci(validated_move.uci))
        next_state = _state_from_board(board)

        outcome = board.outcome(claim_draw=True)
        if outcome is None:
            return transition(next_state, _player_from_turn(board.turn))
        if outcome.winner is None:
            return transition(next_state, None, result=GameResult.DRAW)
        return transition(
            next_state,
            None,
            result=GameResult.WIN,
            winner_player_id=_player_from_turn(outcome.winner),
        )

    def public_state(self, state: dict) -> dict:
        return state

    def observations_for_transition(
        self,
        *,
        event_payload: dict,
        state_before: dict | None,
        state_after: dict,
        settings: ChessSettings | ChessRuntimeSettings | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return open_information_observations(
            event_payload=event_payload,
            state_before=state_before,
            state_after=state_after,
        )


def _board_from_state(state: dict) -> chess.Board:
    return chess.Board(state["fen"])


def _state_from_board(board: chess.Board) -> dict:
    return {
        "fen": board.fen(),
        "turn": _player_from_turn(board.turn),
        "fullmove_number": board.fullmove_number,
        "is_check": board.is_check(),
    }


def _validate_turn(board: chess.Board, player: PlayerId) -> None:
    expected_player = _player_from_turn(board.turn)
    if player != expected_player:
        raise ValueError(f"Expected player {expected_player}")


def _player_from_turn(turn: bool) -> PlayerId:
    return "x" if turn == chess.WHITE else "o"
