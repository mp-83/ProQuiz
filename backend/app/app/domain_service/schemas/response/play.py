from typing import List, NamedTuple, Optional

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from app.domain_service.schemas.response.game import Game


class UIDSchemaBase(BaseModel):
    uid: int

    class Config:
        orm_mode = True


class SimpleAnswer(NamedTuple):
    uid: PositiveInt
    text: str


class Question(BaseModel):
    uid: PositiveInt
    position: NonNegativeInt
    text: str
    time: int = None
    content_url: str = None
    boolean: bool = None
    game: Game = None
    answers_to_display: List[SimpleAnswer] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True


class StartResponse(BaseModel):
    match_uid: PositiveInt
    question: Question
    user_uid: PositiveInt
    attempt_uid: str


class NextResponse(BaseModel):
    match_uid: Optional[PositiveInt]
    question: Question = None
    user_uid: Optional[PositiveInt]
    score: Optional[float]
    was_correct: bool = None

    def dict(self, *args, **kwargs):
        return super(NextResponse, self).dict(exclude_unset=True)


class SignResponse(BaseModel):
    user: PositiveInt
