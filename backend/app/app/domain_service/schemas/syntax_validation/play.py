import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, PositiveInt, validator

from app.constants import (
    ATTEMPT_UID_LENGTH,
    ATTEMPT_UID_POPULATION,
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
        rex = "[" + f"{HASH_POPULATION}" + "]{" + f"{MATCH_HASH_LEN}" + "}$"
        if not re.match(rex, v):
            raise ValueError(f"uHash {v} does not match regex")
        return v


class CodePlay(BaseModel):
    match_code: str

    @validator("match_code")
    def valid(cls, v):
        rex = "[" + f"{CODE_POPULATION}" + "]{" + f"{MATCH_CODE_LEN}" + "}$"
        if not re.match(rex, v):
            raise ValueError(f"Code {v} does not match regex")
        return v


class StartPlay(BaseModel):
    match_uid: PositiveInt
    user_uid: PositiveInt = None
    password: str = None

    @validator("password")
    def valid(cls, v):
        rex = "[" + f"{PASSWORD_POPULATION}" + "]{" + f"{MATCH_PASSWORD_LEN}" + "}$"
        if not re.match(rex, v):
            raise ValueError(f"Password {v} does not match regex")
        return v


class NextPlay(BaseModel):
    match_uid: PositiveInt
    user_uid: PositiveInt
    answer_uid: PositiveInt = None
    question_uid: PositiveInt
    answer_text: str = None
    attempt_uid: str

    @validator("attempt_uid")
    def valid(cls, v):
        rex = "[" + f"{ATTEMPT_UID_POPULATION}" + "]{" + f"{ATTEMPT_UID_LENGTH}" + "}$"
        if not re.match(rex, v):
            raise ValueError(f"Attempt-uid {v} does not match regex")
        return v


class SignPlay(BaseModel):
    email: EmailStr
    token: str

    @validator("email")
    def check_email(cls, v):
        if len(v) > 30:
            raise ValueError()
        return v

    @validator("token")
    def check_token(cls, v):
        if len(v) != 8:
            raise ValueError("Invalid token length")
        return v

    @validator("token")
    def valid_token(cls, v):
        if v is None:
            return

        try:
            datetime.strptime(v, "%d%m%Y")
        except ValueError as err:
            raise ValueError("Invalid token format") from err
        return v
