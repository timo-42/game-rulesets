import chess
from pydantic import BaseModel


class ChessSettings(BaseModel):
    starting_fen: str = chess.STARTING_FEN


class ChessRuntimeSettings(BaseModel):
    starting_fen: str


def resolve_chess_settings(
    settings: ChessSettings | ChessRuntimeSettings | None = None,
) -> ChessRuntimeSettings:
    if isinstance(settings, ChessRuntimeSettings):
        return settings
    settings = settings or ChessSettings()
    return ChessRuntimeSettings.model_validate(settings.model_dump())


def chess_settings_from_snapshot(snapshot: dict) -> ChessRuntimeSettings:
    return ChessRuntimeSettings.model_validate(snapshot)
