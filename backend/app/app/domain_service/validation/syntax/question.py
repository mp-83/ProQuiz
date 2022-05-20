from typing import List, Optional

from pydantic import BaseModel, NonNegativeInt

from app.domain_service.validation.syntax import Answer, AnswerCreate


class Question(BaseModel):
    uid: NonNegativeInt
    position: NonNegativeInt
    text: str
    time: int = None
    content_url: str = None
    answers_list: List[Answer] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True


class QuestionCreate(BaseModel):
    text: str
    position: Optional[NonNegativeInt]
    time: int = None
    content_url: str = None
    game: Optional[NonNegativeInt]
    answers: Optional[List[AnswerCreate]]


class QuestionEdit(QuestionCreate):
    text: Optional[str]
    position: Optional[NonNegativeInt]
