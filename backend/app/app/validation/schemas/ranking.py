from typing import List, Optional

from pydantic import BaseModel


class Match(BaseModel):
    name: str
    uid: int

    class Config:
        orm_mode = True


class User(BaseModel):
    name: Optional[str]
    uid: int

    class Config:
        orm_mode = True


class Ranking(BaseModel):
    uid: int
    match: Match
    user: User
    score: Optional[float]

    class Config:
        orm_mode = True


class MatchRanking(BaseModel):
    rankings: List[Ranking]
