from typing import Optional

from pydantic import BaseModel, NonNegativeInt


class Answer(BaseModel):
    uid: NonNegativeInt
    question_uid: NonNegativeInt
    text: str
    position: NonNegativeInt
    level: Optional[NonNegativeInt]
    is_correct: Optional[bool]
    content_url: Optional[str]


class AnswerCreate(BaseModel):
    text: str
    uid: Optional[NonNegativeInt]
    question_uid: Optional[NonNegativeInt]
    position: Optional[NonNegativeInt]
    level: Optional[NonNegativeInt]
    is_correct: Optional[bool]
    content_url: Optional[str]
