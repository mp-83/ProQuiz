from typing import Optional

from pydantic import BaseModel, NonNegativeInt, validator


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

    @validator("text")
    def coerce_boolean_text(cls, v):
        false = {
            "off",
            "F",
            "OFF",
            "N",
            "No",
            "FALSE",
            "f",
            "NO",
            "n",
            "no",
            "Off",
            "false",
            "False",
        }
        truth = {
            "Y",
            "Yes",
            "True",
            "YES",
            "on",
            "y",
            "true",
            "t",
            "On",
            "T",
            "TRUE",
            "ON",
            "yes",
        }

        if v in false:
            v = "False"
        elif v in truth:
            v = "True"

        return v


class AnswerEdit(BaseModel):
    uid: NonNegativeInt
    text: Optional[str]
