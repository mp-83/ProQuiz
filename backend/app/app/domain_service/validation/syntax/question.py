from typing import List, Optional

from pydantic import BaseModel, HttpUrl, NonNegativeInt, validator

from app.constants import QUESTION_TEXT_MAX_LENGTH, QUESTION_TEXT_MIN_LENGTH
from app.domain_service.validation.syntax import Answer, AnswerCreate, Game


class Question(BaseModel):
    uid: NonNegativeInt
    position: NonNegativeInt
    text: str
    time: int = None
    content_url: str = None
    game: Game = None
    answers_list: List[Answer] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True


class QuestionCreate(BaseModel):
    text: Optional[str]
    position: Optional[NonNegativeInt]
    time: int = None
    content_url: Optional[HttpUrl]
    game: Optional[NonNegativeInt]
    answers: Optional[List[AnswerCreate]]

    @validator("text")
    def text_length(cls, value: str):
        if value:
            assert QUESTION_TEXT_MIN_LENGTH <= len(value) < QUESTION_TEXT_MAX_LENGTH
        return value


class QuestionEdit(QuestionCreate):
    text: Optional[str]
    position: Optional[NonNegativeInt]


class ManyQuestions(BaseModel):
    questions: List[Question]
