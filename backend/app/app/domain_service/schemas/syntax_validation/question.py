from typing import List, Optional

from pydantic import BaseModel, HttpUrl, NonNegativeInt, PrivateAttr, validator

from app.constants import QUESTION_TEXT_MAX_LENGTH, QUESTION_TEXT_MIN_LENGTH
from app.domain_service.schemas.syntax_validation import Answer, AnswerCreate, Game


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

    _initial_fields: List = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._initial_fields = list(data.keys())

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data["_initial_fields"] = self._initial_fields
        return data
