from pydantic import BaseModel, PositiveInt

from app.domain_service.schemas.response.question import Question


class UIDSchemaBase(BaseModel):
    uid: int

    class Config:
        orm_mode = True


class StartResponse(BaseModel):
    match_uid: PositiveInt
    question: Question
    user_uid: PositiveInt


class NextResponse(BaseModel):
    match_uid: PositiveInt = None
    question: Question = None
    user_uid: PositiveInt = None
    score: int = None


class SignResponse(BaseModel):
    user: PositiveInt
