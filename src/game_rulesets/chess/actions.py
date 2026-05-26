from pydantic import BaseModel, Field


class ChessMove(BaseModel):
    uci: str = Field(min_length=4, max_length=5)
