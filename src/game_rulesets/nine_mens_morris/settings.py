from pydantic import BaseModel, PositiveInt


class NineMensMorrisSettings(BaseModel):
    pieces_per_player: PositiveInt = 9
    flying_enabled: bool = True


class NineMensMorrisRuntimeSettings(BaseModel):
    pieces_per_player: PositiveInt
    flying_enabled: bool


def resolve_nine_mens_morris_settings(
    settings: NineMensMorrisSettings | NineMensMorrisRuntimeSettings | None = None,
) -> NineMensMorrisRuntimeSettings:
    if isinstance(settings, NineMensMorrisRuntimeSettings):
        return settings
    settings = settings or NineMensMorrisSettings()
    return NineMensMorrisRuntimeSettings.model_validate(settings.model_dump())


def nine_mens_morris_settings_from_snapshot(snapshot: dict) -> NineMensMorrisRuntimeSettings:
    return NineMensMorrisRuntimeSettings.model_validate(snapshot)
