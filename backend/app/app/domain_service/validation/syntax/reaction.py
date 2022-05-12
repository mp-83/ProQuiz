from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domain_service.validation.syntax import Answer, Game, Match, Question


class Reaction(BaseModel):
    match_uid: int
    match: Optional[Match]
    user_uid: int
    answer_uid: int
    answer: Optional[Answer]
    game_uid: int
    game: Optional[Game]
    question_uid: int
    question: Optional[Question]
    dirty: Optional[bool]
    answer_time: Optional[datetime]
    score: Optional[float]
