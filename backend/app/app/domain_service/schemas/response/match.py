from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.domain_service.schemas.syntax_validation.game import Game
from app.domain_service.schemas.syntax_validation.question import Question


class Match(BaseModel):
    uid: Optional[int]
    name: Optional[str]
    uhash: Optional[str]
    code: Optional[str]
    password: Optional[str]
    is_restricted: Optional[bool]
    from_time: Optional[datetime]
    times: Optional[int]
    order: Optional[bool]
    expires: Optional[datetime]
    questions_list: List[Question] = None
    games_list: List[Game] = None

    class Config:
        orm_mode = True


class Matches(BaseModel):
    matches: List[Match] = []
