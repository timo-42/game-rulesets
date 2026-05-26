from pydantic import BaseModel, Field


class CheckersSquare(BaseModel):
    row: int = Field(ge=0, le=7)
    col: int = Field(ge=0, le=7)


class CheckersMove(BaseModel):
    path: tuple[CheckersSquare, ...] = Field(min_length=2)
