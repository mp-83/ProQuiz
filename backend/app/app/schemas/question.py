from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from app.schemas.game import Game
from app.schemas.answer import Answer


class Question(BaseModel):
    uid: int
    position: int
    text: str
    time: int = None
    content_url: str = None
    # answers = List[Answer]
