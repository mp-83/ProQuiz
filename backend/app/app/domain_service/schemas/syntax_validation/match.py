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


class MatchEdit(BaseModel):
    name: Optional[str]
    times: Optional[int]
    is_restricted: Optional[bool]
    order: Optional[bool]
    from_time: Optional[datetime]
    to_time: Optional[datetime]
    questions: List[QuestionCreate] = None
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
    uid: int
    data: FileContent

    @validator("data", pre=True)
    def coerce(cls, value):
        value = cls.coerce_to_b64content(value)
        value = cls.coerce_yaml_content(value)
        return cls.to_expected_mapping(value)

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
    def to_expected_mapping(cls, value):
        result = {"questions": []}
        question = {}
        for i, elem in enumerate(value.get("questions")):
            if i % 2 == 0:
                question["text"] = elem
            else:
                question["answers"] = [{"text": text} for text in elem["answers"]]
                result["questions"].append(question)
                question = {}
        return result
