from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel
from app.schemas import Match, User, Answer, Game, Question



class Reaction(BaseModel):
    match_uid: int
    match: Optional[Match]
    user_uid: int
    user: Optional[User]
    answer_uid: int
    answer: Optional[Answer]
    game_uid: int
    game: Optional[Game]
    question_uid: int
    question: Optional[Question]
    dirty: Optional[bool]
    answer_time: Optional[datetime]
    score: Optional[float]
