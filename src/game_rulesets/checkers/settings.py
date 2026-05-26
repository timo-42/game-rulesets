from pydantic import BaseModel


class CheckersSettings(BaseModel):
    mandatory_capture: bool = True


class CheckersRuntimeSettings(BaseModel):
    mandatory_capture: bool


def resolve_checkers_settings(
    settings: CheckersSettings | CheckersRuntimeSettings | None = None,
) -> CheckersRuntimeSettings:
    if isinstance(settings, CheckersRuntimeSettings):
        return settings
    settings = settings or CheckersSettings()
    return CheckersRuntimeSettings.model_validate(settings.model_dump())


def checkers_settings_from_snapshot(snapshot: dict) -> CheckersRuntimeSettings:
    return CheckersRuntimeSettings.model_validate(snapshot)
