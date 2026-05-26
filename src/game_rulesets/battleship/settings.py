from typing import Annotated

from pydantic import BaseModel, Field, PositiveInt


class BattleshipSettings(BaseModel):
    rows: PositiveInt = 10
    columns: PositiveInt = 10
    ship_lengths: tuple[PositiveInt, ...] = (5, 4, 3, 3, 2)


class BattleshipRuntimeSettings(BaseModel):
    rows: PositiveInt
    columns: PositiveInt
    ship_lengths: Annotated[tuple[PositiveInt, ...], Field(min_length=1)]


def resolve_battleship_settings(
    settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
) -> BattleshipRuntimeSettings:
    if isinstance(settings, BattleshipRuntimeSettings):
        return settings
    settings = settings or BattleshipSettings()
    return BattleshipRuntimeSettings.model_validate(settings.model_dump())


def battleship_settings_from_snapshot(snapshot: dict) -> BattleshipRuntimeSettings:
    return BattleshipRuntimeSettings.model_validate(snapshot)
