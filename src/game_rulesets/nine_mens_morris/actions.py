from typing import Literal

from pydantic import BaseModel, model_validator


class NineMensMorrisMove(BaseModel):
    action: Literal["place", "move"]
    position: str | None = None
    from_position: str | None = None
    to_position: str | None = None
    remove_position: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "NineMensMorrisMove":
        if self.action == "place":
            if self.position is None:
                raise ValueError("Place actions require position")
            if self.from_position is not None or self.to_position is not None:
                raise ValueError("Place actions cannot include from_position or to_position")
            return self
        if self.from_position is None or self.to_position is None:
            raise ValueError("Move actions require from_position and to_position")
        if self.position is not None:
            raise ValueError("Move actions cannot include position")
        return self
