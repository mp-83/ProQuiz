from typing import List, Optional

from pydantic import BaseModel

from app.schemas import Answer


class SimpleAnswer(BaseModel):
    text: str


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
    time: int = None
    content_url: str = None
    game: Optional[int]
    answers: List[SimpleAnswer]
