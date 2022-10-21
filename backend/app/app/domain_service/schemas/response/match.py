from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.domain_service.schemas.syntax_validation.game import Game
from app.domain_service.schemas.syntax_validation.question import Question


class User(BaseModel):
    name: Optional[str]
    uid: int

    class Config:
        orm_mode = True


class Ranking(BaseModel):
    uid: int
    user: User
    score: Optional[float]

    class Config:
        orm_mode = True


class MatchRanking(BaseModel):
    name: str
    rankings: List[Ranking]

    class Config:
        orm_mode = True


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
    is_open: Optional[bool]
    expires: Optional[datetime]
    questions_list: List[Question] = None
    games_list: List[Game] = None

    class Config:
        orm_mode = True


class Matches(BaseModel):
    matches: List[Match] = []
