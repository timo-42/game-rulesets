from pydantic import BaseModel, Field


class TicTacToeMove(BaseModel):
    row: int = Field(ge=0)
    col: int = Field(ge=0)
