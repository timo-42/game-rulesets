from typing import Literal

from pydantic import BaseModel

AxelrodChoice = Literal["cooperate", "defect"]


class AxelrodMove(BaseModel):
    choice: AxelrodChoice
