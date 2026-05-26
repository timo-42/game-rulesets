from pydantic import BaseModel, Field, PositiveInt


class GoSettings(BaseModel):
    board_size: PositiveInt = Field(default=19, le=25)
    komi: float = 7.5


class GoRuntimeSettings(BaseModel):
    board_size: PositiveInt = Field(le=25)
    komi: float


def resolve_go_settings(
    settings: GoSettings | GoRuntimeSettings | None = None,
) -> GoRuntimeSettings:
    if isinstance(settings, GoRuntimeSettings):
        return settings
    settings = settings or GoSettings()
    return GoRuntimeSettings.model_validate(settings.model_dump())


def go_settings_from_snapshot(snapshot: dict) -> GoRuntimeSettings:
    return GoRuntimeSettings.model_validate(snapshot)
