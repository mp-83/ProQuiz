from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from app.schemas.question import Question


class Match(BaseModel):
    uid: int
    name: str
    uhash: Optional[str]
    code: Optional[str]
    password: Optional[str]
    is_restricted: Optional[bool]
    from_time: Optional[datetime]
    to_time: Optional[datetime]
    times: Optional[int]
    order: Optional[bool]
    expires: Optional[str]
    questions: List[Question]
