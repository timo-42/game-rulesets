from typing import Annotated

from pydantic import BaseModel, Field, PositiveInt


class ConnectFourSettings(BaseModel):
    rows: PositiveInt = 6
    columns: PositiveInt = 7
    win_length: Annotated[int, Field(ge=2)] = 4


class ConnectFourRuntimeSettings(BaseModel):
    rows: PositiveInt
    columns: PositiveInt
    win_length: Annotated[int, Field(ge=2)]


def resolve_connect_four_settings(
    settings: ConnectFourSettings | ConnectFourRuntimeSettings | None = None,
) -> ConnectFourRuntimeSettings:
    if isinstance(settings, ConnectFourRuntimeSettings):
        return settings
    settings = settings or ConnectFourSettings()
    return ConnectFourRuntimeSettings.model_validate(settings.model_dump())


def connect_four_settings_from_snapshot(snapshot: dict) -> ConnectFourRuntimeSettings:
    return ConnectFourRuntimeSettings.model_validate(snapshot)
