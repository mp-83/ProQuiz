from typing import Optional

from pydantic import BaseModel
from app.schemas.match import Match
from app.schemas.user import User


class Ranking(BaseModel):
    uid: int
    match: Match
    user: User
    score: Optional[int]


