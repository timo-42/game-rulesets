from typing import Annotated

from pydantic import BaseModel, Field, PositiveInt, model_validator


class AxelrodTournamentSettings(BaseModel):
    rounds: PositiveInt = 200
    mutual_cooperation_payoff: Annotated[int, Field(ge=0)] = 3
    temptation_payoff: Annotated[int, Field(ge=0)] = 5
    punishment_payoff: Annotated[int, Field(ge=0)] = 1
    sucker_payoff: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def validate_prisoners_dilemma_payoffs(self) -> "AxelrodTournamentSettings":
        if not (
            self.temptation_payoff
            > self.mutual_cooperation_payoff
            > self.punishment_payoff
            > self.sucker_payoff
        ):
            raise ValueError(
                "Payoffs must satisfy temptation > mutual cooperation > punishment > sucker"
            )
        return self


AxelrodTournamentRuntimeSettings = AxelrodTournamentSettings


def resolve_axelrod_tournament_settings(
    settings: AxelrodTournamentSettings | AxelrodTournamentRuntimeSettings | None = None,
) -> AxelrodTournamentRuntimeSettings:
    return settings or AxelrodTournamentSettings()


def axelrod_tournament_settings_from_snapshot(snapshot: dict) -> AxelrodTournamentRuntimeSettings:
    return AxelrodTournamentRuntimeSettings.model_validate(snapshot)
