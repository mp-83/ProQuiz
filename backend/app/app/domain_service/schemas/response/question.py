from typing import List

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from app.domain_service.schemas.response.answer import Answer
from app.domain_service.schemas.response.game import Game


class Question(BaseModel):
    uid: PositiveInt
    position: NonNegativeInt
    text: str
    time: int = None
    content_url: str = None
    boolean: bool = None
    game: Game = None
    answers_list: List[Answer] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True


class ManyQuestions(BaseModel):
    questions: List[Question]
