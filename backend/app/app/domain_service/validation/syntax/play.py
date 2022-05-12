import re
from datetime import datetime

from pydantic import BaseModel, ValidationError, validator

from app.constants import (
    CODE_POPULATION,
    HASH_POPULATION,
    MATCH_CODE_LEN,
    MATCH_HASH_LEN,
    MATCH_PASSWORD_LEN,
    PASSWORD_POPULATION,
)


class PlaySchemaBase(BaseModel):
    uid: int

    class Config:
        orm_mode = True


class LandPlay(BaseModel):
    match_uhash: str

    @validator("match_uhash")
    def valid(cls, v):
        rex = "[" + f"{HASH_POPULATION}" + "]{" + f"{MATCH_HASH_LEN}" + "}"
        if not re.match(rex, v):
            raise ValueError(f"uHash {v} does not match regex")
        return v


class CodePlay(BaseModel):
    match_code: str

    @validator("match_code")
    def valid(cls, v):
        rex = "[" + f"{CODE_POPULATION}" + "]{" + f"{MATCH_CODE_LEN}" + "}"
        if not re.match(rex, v):
            raise ValueError(f"Code {v} does not match regex")
        return v


class StartPlay(BaseModel):
    match_uid: int
    user_uid: int = None
    password: str = None

    @validator("match_uid", "user_uid")
    def greater_than_one(cls, v):
        if v < 1:
            raise ValidationError()
        return v

    @validator("password")
    def valid(cls, v):
        rex = "[" + f"{PASSWORD_POPULATION}" + "]{" + f"{MATCH_PASSWORD_LEN}" + "}"
        if not re.match(rex, v):
            raise ValueError(f"Password {v} does not match regex")
        return v


class NextPlay(BaseModel):
    match_uid: int
    user_uid: int
    answer_uid: int
    question_uid: int

    @validator("*")
    def greater_than_one(cls, v):
        if v < 1:
            raise ValidationError()
        return v


class SignPlay(BaseModel):
    email: str
    token: str

    @validator("email")
    def check_email(cls, v):
        if len(v) > 30:
            raise ValidationError()
        return v

    @validator("email")
    def valid_email(cls, v):
        rex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]{2,}\.[a-zA-Z]{2,}"
        if not re.match(rex, v):
            raise ValidationError()
        return v

    @validator("token")
    def check_token(cls, v):
        if len(v) != 8:
            raise ValidationError()
        return v

    @validator("token")
    def valid_token(cls, v):
        if v is None:
            return

        try:
            datetime.strptime(v, "%d%m%Y")
        except ValueError as err:
            raise ValidationError("Invalid data format") from err
        return v
