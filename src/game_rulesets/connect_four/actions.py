from pydantic import BaseModel, Field


class ConnectFourMove(BaseModel):
    column: int = Field(ge=0)
