from pydantic import BaseModel, PositiveInt


class TicTacToeSettings(BaseModel):
    rows: PositiveInt = 3
    columns: PositiveInt = 3


class TicTacToeRuntimeSettings(BaseModel):
    rows: PositiveInt
    columns: PositiveInt


def resolve_tic_tac_toe_settings(
    settings: TicTacToeSettings | TicTacToeRuntimeSettings | None = None,
) -> TicTacToeRuntimeSettings:
    if isinstance(settings, TicTacToeRuntimeSettings):
        return settings
    settings = settings or TicTacToeSettings()
    return TicTacToeRuntimeSettings.model_validate(settings.model_dump())


def tic_tac_toe_settings_from_snapshot(snapshot: dict) -> TicTacToeRuntimeSettings:
    return TicTacToeRuntimeSettings.model_validate(snapshot)
