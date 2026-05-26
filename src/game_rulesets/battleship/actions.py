from typing import Literal

from pydantic import BaseModel, Field


class BattleshipShipPlacement(BaseModel):
    length: int = Field(ge=1)
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    orientation: Literal["horizontal", "vertical"]


class BattleshipFleetSetup(BaseModel):
    ships: list[BattleshipShipPlacement]


class BattleshipShot(BaseModel):
    row: int = Field(ge=0)
    col: int = Field(ge=0)
