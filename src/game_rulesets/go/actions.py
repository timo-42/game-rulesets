from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GoMove(BaseModel):
    move: Literal["play", "pass"] = "play"
    row: int | None = Field(default=None, ge=0)
    col: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "GoMove":
        if self.move == "pass":
            if self.row is not None or self.col is not None:
                raise ValueError("Pass moves cannot include coordinates")
            return self
        if self.row is None or self.col is None:
            raise ValueError("Play moves require row and col")
        return self
