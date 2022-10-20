import re
from base64 import b64decode
from datetime import datetime
from typing import List, Optional

import yaml
from pydantic import BaseModel, PositiveInt, PrivateAttr, validator

from app.domain_service.schemas.syntax_validation.question import QuestionCreate


class MatchCreate(BaseModel):
    name: str = None
    with_code: Optional[bool]
    times: Optional[int] = None
    from_time: Optional[datetime]
    to_time: Optional[datetime]
    is_restricted: Optional[bool]
    order: Optional[bool]
    questions: List[QuestionCreate] = None


class GameEdit(BaseModel):
    uid: PositiveInt
    order: bool


class MatchEdit(BaseModel):
    name: Optional[str]
    times: Optional[int]
    is_restricted: Optional[bool]
    order: Optional[bool]
    from_time: Optional[datetime]
    to_time: Optional[datetime]
    questions: List[QuestionCreate] = None
    games: List[GameEdit] = None
    _initial_fields: List = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._initial_fields = list(data.keys())

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data["_initial_fields"] = self._initial_fields
        return data


class ImportQuestions(BaseModel):
    uid: PositiveInt
    questions: List[PositiveInt] = None
    game_uid: PositiveInt = None


class FileContent(BaseModel):
    questions: List[QuestionCreate] = None


class MatchYamlImport(BaseModel):
    uid: PositiveInt
    data: FileContent
    game_uid: PositiveInt = None

    @validator("data", pre=True)
    def coerce(cls, value):
        value = cls.coerce_to_b64content(value)
        value = cls.coerce_yaml_content(value)
        if cls.is_open_match(value):
            return cls.open_match_structure(value)
        return cls.fixed_match_structure(value)

    @classmethod
    def coerce_yaml_content(cls, value):
        if not value:
            return ""

        try:
            return yaml.load(value, yaml.Loader)
        except yaml.parser.ParserError as err:
            raise ValueError("Content cannot be coerced") from err

    @classmethod
    def coerce_to_b64content(cls, value):
        b64content = re.sub(r"data:application/x-yaml;base64,", "", value)
        return b64decode(b64content)

    @classmethod
    def is_open_match(cls, value):
        return all("answers" not in elem for elem in value.get("questions") if elem)

    @classmethod
    def fixed_match_structure(cls, value):
        result = {"questions": []}
        question = {}
        for i, elem in enumerate(value.get("questions"), start=1):
            if i % 3 == 1 and elem and "text" in elem:
                question["text"] = elem["text"]
            elif i % 3 == 2 and elem and "time" in elem:
                question["time"] = elem["time"]
            elif i % 3 == 0:
                question["answers"] = [
                    {"text": text} for text in elem.get("answers") or []
                ]
                if question.get("text") is None:
                    question = {}
                    continue
                result["questions"].append(question)
                question = {}
        return result

    @classmethod
    def open_match_structure(cls, value):
        result = {"questions": []}
        question = {}
        for i, elem in enumerate(value.get("questions"), start=1):
            if i % 2 == 1 and elem and "text" in elem:
                question["text"] = elem["text"]
            elif i % 2 == 0 and elem and "time" in elem:
                question["time"] = elem["time"]
                question["answers"] = []
                result["questions"].append(question)
                question = {}
        return result
