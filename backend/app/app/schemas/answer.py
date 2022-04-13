from typing import Optional

from pydantic import BaseModel


class Answer(BaseModel):
    uid: int
    question_uid: int
    text: str
    position: int
    level: Optional[int]
    is_correct: Optional[bool]
    content_url: Optional[str]

