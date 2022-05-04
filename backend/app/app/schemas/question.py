from typing import List, Optional

from pydantic import BaseModel, validator

from app.schemas import Answer


class SimpleAnswer(BaseModel):
    uid: Optional[int]
    text: str

    @validator("uid")
    def positive_value(cls, v):
        if v is not None:
            assert v > 0
        return v


class Question(BaseModel):
    uid: int
    position: int
    text: str
    time: int = None
    content_url: str = None
    answers_list: List[Answer] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True


class QuestionCreate(BaseModel):
    text: str
    position: int
    time: int = None
    content_url: str = None
    game_uid: Optional[int]
    answers: List[SimpleAnswer] = []

    @validator("position")
    def positive_value(cls, v):
        assert v > 0
        return v


class QuestionEdit(QuestionCreate):
    text: Optional[str]
    position: Optional[int]

    @validator("position")
    def positive_value(cls, v):
        if v is not None:
            assert v > 0
        return v
