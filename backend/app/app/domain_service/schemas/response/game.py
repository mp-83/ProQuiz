from typing import Optional

from pydantic import BaseModel


class Game(BaseModel):
    uid: int
    match_uid: int
    index: int
    order: Optional[bool]

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
