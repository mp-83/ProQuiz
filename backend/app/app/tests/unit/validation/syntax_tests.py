from base64 import b64encode
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain_service.schemas import syntax_validation as syntax


class TestCaseNullable:
    def test_1(self):
        for schema, field in [
            (syntax.LandPlay, "match_uhash"),
            (syntax.CodePlay, "match_code"),
        ]:
            with pytest.raises(ValidationError) as err:
                schema(**{field: None})
            assert err.value.errors()[0]["msg"] == "none is not an allowed value"


class TestCasePlaySchemas:
    def test_1(self):
        value = "IJD34KOP"
        with pytest.raises(ValidationError) as err:
            syntax.LandPlay(**{"match_uhash": value})

        assert err.value.errors()[0]["msg"] == f"uHash {value} does not match regex"

    def test_2(self):
        value = "34569"
        with pytest.raises(ValidationError) as err:
            syntax.CodePlay(**{"match_code": value})
        assert err.value.errors()[0]["msg"] == f"Code {value} does not match regex"

    def test_3(self):
        assert syntax.StartPlay(**{"match_uid": 1})

    def test_4(self):
        assert syntax.StartPlay(**{"match_uid": 1, "user_uid": 1})

    def test_5(self):
        """
        invalid password string
        """
        password = "IJD34KOP"
        with pytest.raises(ValidationError) as err:
            syntax.StartPlay(**{"match_uid": 1, "user_uid": 1, "password": password})

        assert (
            err.value.errors()[0]["msg"] == f"Password {password} does not match regex"
        )

    def test_6(self):
        """
        valid password string
        """
        schema = syntax.StartPlay(
            **{"match_uid": 1, "user_uid": 1, "password": "04542"}
        )
        assert schema.dict()["password"] == "04542"

    def test_7(self):
        """
        correct/valid payload
        """
        assert syntax.NextPlay(
            **{
                "match_uid": 1,
                "user_uid": 2,
                "answer_uid": 3,
                "question_uid": 4,
                "attempt_uid": "40dd7e2d1c5a4a25adc2d3a5367b8de3",
            }
        )

    def test_8(self):
        """
        question_uid is required
        """
        with pytest.raises(ValidationError) as err:
            syntax.NextPlay(
                **{
                    "match_uid": 1,
                    "user_uid": 2,
                    "answer_uid": 3,
                    "attempt_uid": "40dd7e2d1c5a4a25adc2d3a5367b8de3",
                }
            )

        assert err.value.errors()[0]["loc"] == ("question_uid",)
        assert err.value.errors()[0]["msg"] == "field required"

    def test_9(self):
        """
        no error is raised because the data matches the expected format (token: ddmmyyyy)
        """
        assert syntax.SignPlay(**{"email": "user@pp.com", "token": "12022021"})

    def test_10(self):
        """
        token cannot be null
        """
        with pytest.raises(ValidationError) as err:
            syntax.SignPlay(**{"email": "user@pp.com", "token": None})

        assert err.value.errors()[0]["loc"] == ("token",)
        assert err.value.errors()[0]["msg"] == "none is not an allowed value"

    def test_11(self):
        """
        email cannot be null
        """
        with pytest.raises(ValidationError) as err:
            syntax.SignPlay(**{"email": None, "token": "11012014"})

        assert err.value.errors()[0]["loc"] == ("email",)
        assert err.value.errors()[0]["msg"] == "none is not an allowed value"

    def test_12(self):
        """
        GIVEN: payload with an answer text,
            either empty or valued
        WHEN: validation is run
        THEN: no error should be raised
        """
        assert syntax.NextPlay(
            **{
                "match_uid": 1,
                "user_uid": 2,
                "answer_text": "Open answer text",
                "question_uid": 4,
                "attempt_uid": "40dd7e2d1c5a4a25adc2d3a5367b8de3",
            }
        )

    def test_13(self):
        """
        a null attempt_uid
        """
        with pytest.raises(ValidationError) as err:
            syntax.NextPlay(
                **{
                    "match_uid": 1,
                    "user_uid": 2,
                    "answer_text": "Open answer text",
                    "question_uid": 4,
                    "attempt_uid": None,
                }
            )
        assert err.value.errors()[0]["loc"] == ("attempt_uid",)
        assert err.value.errors()[0]["msg"] == "none is not an allowed value"

    def test_14(self):
        """
        payload with an invalid attempt_uid,
        """
        value = "40dz7e2d1c5a4a25adc2d3a5367b8dew"
        with pytest.raises(ValidationError) as err:
            syntax.NextPlay(
                **{
                    "match_uid": 1,
                    "user_uid": 2,
                    "answer_text": "Open answer text",
                    "question_uid": 4,
                    "attempt_uid": value,
                }
            )
        assert err.value.errors()[0]["loc"] == ("attempt_uid",)
        assert (
            err.value.errors()[0]["msg"] == f"Attempt-uid {value} does not match regex"
        )


class TestCaseQuestionSchema:
    def test_1(self):
        """
        text longer than maxLen
        """
        pytest.raises(
            ValidationError,
            syntax.QuestionCreate,
            **{"text": "".join("a" for _ in range(501)), "position": 1},
        )

    def test_2(self):
        """
        text shorter than minLen
        """
        pytest.raises(ValidationError, syntax.QuestionCreate, text="aa", position=1)

    def test_3(self):
        """
        text NULL
        """
        assert syntax.QuestionCreate(text=None, position=1)

    def test_4(self):
        """
        content-url NULL
        """
        assert syntax.QuestionCreate(content_url=None)

    def test_5(self):
        """
        content-url string shorter than minLen
        """
        pytest.raises(
            ValidationError, syntax.QuestionCreate, content_url="aa", position=1
        )


class TestCaseMatchSchema:
    def test_1(self):
        """
        values are cast to their pythonic correspondent
        """
        schema = syntax.MatchCreate(
            **{
                "name": "new match",
                "times": "2",
                "is_restricted": "true",
                "questions": [
                    {
                        "text": "Austria is in Europe?",
                        "answers": [
                            {"text": "false"},
                            {"text": "true"},
                        ],
                    },
                ],
            }
        )
        assert schema
        assert schema.dict()["is_restricted"] is True
        answers = schema.dict()["questions"][0]["answers"]
        assert answers[0]["text"] == "False"
        assert answers[1]["text"] == "True"

    def test_2(self):
        """
        to_time and from_time can be null as they optional
        """
        assert syntax.MatchCreate(
            **{
                "name": "new match",
                "with_code": "true",
                "questions": [],
                "to_time": None,
                "from_time": None,
            }
        )

    def test_3(self):
        """
        valid to_time and from_time values
        """
        schema = syntax.MatchCreate(
            **{
                "name": "new match",
                "times": "2",
                "with_code": "true",
                "questions": [],
                "from_time": "2022-03-19T16:10:39.135166",
                "to_time": "2022-03-19T16:10:39.935155",
            }
        )
        assert schema
        assert isinstance(schema.dict()["to_time"], datetime)

    def test_4(self):
        """
        a set of edge values for the field times
        """
        document = {
            "name": "new match",
            "times": "2",
            "is_restricted": "true",
            "with_code": "true",
            "order": "false",
            "questions": [{"text": "text"}],
        }
        for value in [1, None, "10"]:
            document.update(times=value)
            schema = syntax.MatchCreate(**document)
            assert schema
            assert schema.dict()["with_code"]

    def test_5(self):
        """
        valid payload, values are cast as expected
        """
        schema = syntax.MatchEdit(
            **{
                "from_time": "2022-01-01T00:00:01+00:00",
                "to_time": "2022-12-31T23:59:59+00:00",
            }
        )
        assert schema
        assert isinstance(schema.dict()["from_time"], datetime)
        assert schema.dict()["from_time"].tzinfo
        assert isinstance(schema.dict()["to_time"], datetime)
        assert schema.dict()["to_time"].tzinfo


class TestCaseYamlSchema:
    @pytest.fixture
    def valid_encoded_yaml_content(self):
        document = """
          questions:
            - text: Where is Adelaide?
            - time: 5
            - answers:
              - Australia
              - Japan
              - Kenya
            - text: Where is Paris?
            - time:
            - answers:
               - France
               - Argentina
               - Iceland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"
        yield b64string

    def test_1(self, valid_encoded_yaml_content):
        """
        valid yaml content
        """
        schema = syntax.MatchYamlImport(
            **{"uid": 1, "data": valid_encoded_yaml_content}
        )
        assert schema
        data = schema.dict()["data"]
        assert len(data["questions"]) == 2
        assert data["questions"][0]["text"] == "Where is Adelaide?"
        assert data["questions"][0]["time"] == 5
        assert {e["text"] for e in data["questions"][0]["answers"]} == {
            "Australia",
            "Japan",
            "Kenya",
        }

    def test_2(self):
        """
        invalid payload because the key `answers` is not
        prefixed with dash
        """
        document = """
          questions:
            - text: Where is Belfast?
            answers:
              - Sweden
              - England
              - Ireland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        with pytest.raises(ValidationError) as err:
            syntax.MatchYamlImport(**{"uid": 1, "data": b64string})

        assert err.value.errors()[0]["msg"] == "Content cannot be coerced"

    def test_3(self, valid_encoded_yaml_content):
        """
        invalid payload because the bytes have an invalid padding
        """
        with pytest.raises(ValidationError) as err:
            syntax.MatchYamlImport(
                **{"uid": 1, "data": valid_encoded_yaml_content[:-1]}
            )
        assert err.value.errors()[0]["msg"] == "Incorrect padding"

    def test_4(self):
        """
        GIVEN: a yaml file with question text blank
        WHEN: validation is run
        THEN: no error is raised but the answers are ignored
        """
        document = """
          questions:
            - text:
            - time: 10
            - answers:
              - Sweden
              - England
              - Ireland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        schema = syntax.MatchYamlImport(**{"uid": 1, "data": b64string})
        assert schema.dict() == {"uid": 1, "data": {"questions": []}, "game_uid": None}

    def test_5(self):
        """
        GIVEN: a yaml file with missing question key
        WHEN: validation is run
        THEN: no error is raised but the answers are ignored
                because there is not related question (no text)
        """
        document = """
          questions:
            - answers:
              - Sweden
              - England
              - Ireland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        schema = syntax.MatchYamlImport(**{"uid": 1, "data": b64string, "game_uid": 3})
        assert schema
        assert schema.dict() == {"uid": 1, "data": {"questions": []}, "game_uid": 3}

    def test_6(self):
        """
        fixed_match_structure returns the expected result
        """
        value = {
            "questions": [
                {"text": None},
                {"time": None},
                {"answers": ["Australia", "Japan", "Kenya"]},
                {"text": "Where is Paris?"},
                {"time": 10},
                {"answers": ["France", "Argentina", "Iceland"]},
            ]
        }

        result = syntax.MatchYamlImport.fixed_match_structure(value)
        assert result == {
            "questions": [
                {
                    "text": "Where is Paris?",
                    "time": 10,
                    "answers": [
                        {"text": "France"},
                        {"text": "Argentina"},
                        {"text": "Iceland"},
                    ],
                },
            ]
        }

    def test_7(self):
        """
        GIVEN: a data structure mapping an open match
                without `answers`
        WHEN: is_open_match is called
        THEN: it should return True
        """
        value = {
            "questions": [
                {"text": "Where is Austin?"},
                {"time": None},
                {"text": "Where is Dallas?"},
                {"time": 10},
            ]
        }

        assert syntax.MatchYamlImport.is_open_match(value)

    def test_8(self):
        """
        GIVEN: a data structure mapping an open match
                with `answers` provided
        WHEN: is_open_match is called
        THEN: it should return False
        """
        value = {
            "questions": [
                {"text": "Where is Austin?"},
                {"time": None},
                {"answers": ["Texas", "Georgia", "Montana"]},
                {"text": "Where is Dallas?"},
                {"time": 10},
                {"answers": ["Florida", "Ohio", "Kentucky"]},
            ]
        }

        assert not syntax.MatchYamlImport.is_open_match(value)

    def test_9(self):
        """
        GIVEN: this value object
        WHEN: fixed_match_structure is invoked
        THEN: produces the expected result
        """
        value = {
            "questions": [
                {"text": None},
                {"time": None},
                {"answers": ["Australia", "Japan", "Kenya"]},
                {"text": "Where is Paris?"},
                {"time": 10},
                {"answers": ["France", "Argentina", "Iceland"]},
            ]
        }

        result = syntax.MatchYamlImport.fixed_match_structure(value)
        assert result == {
            "questions": [
                {
                    "text": "Where is Paris?",
                    "time": 10,
                    "answers": [
                        {"text": "France"},
                        {"text": "Argentina"},
                        {"text": "Iceland"},
                    ],
                },
            ]
        }

    def test_10(self):
        """
        GIVEN: this value object
        WHEN: open_match_structure is invoked
        THEN: produces the expected result
        """
        value = {
            "questions": [
                {"text": "Where is Austin?"},
                {"time": None},
                {"text": "Where is Dallas?"},
                {"time": 10},
            ]
        }

        result = syntax.MatchYamlImport.open_match_structure(value)
        assert result == {
            "questions": [
                {
                    "text": "Where is Austin?",
                    "time": None,
                    "answers": [],
                },
                {
                    "text": "Where is Dallas?",
                    "time": 10,
                    "answers": [],
                },
            ]
        }


class TestCaseUserSchema:
    def test_1(self):
        """
        email cannot be empty
        """
        with pytest.raises(ValidationError) as err:
            syntax.SignedUserCreate(**{"email": "", "token": "02031980"})

        assert err.value.errors()[0]["msg"] == "value is not a valid email address"

    def test_2(self):
        """
        valid email value
        """
        schema = syntax.SignedUserCreate(**{"email": "e@a.cc", "token": "02031980"})
        assert schema.dict() == {"email": "e@a.cc", "token": "02031980"}

    def test_3(self):
        """
        GIVEN: a payload to create a signed user
        WHEN: validation is run
        THEN: an error is raised because the token doesn't match
                the format ddmmyyyy
        """
        with pytest.raises(ValidationError) as err:
            syntax.SignedUserCreate(**{"email": "test@proquiz.com", "token": "0203197"})
        assert err.value.errors()[0]["msg"] == "Invalid token length"

    def test_4(self):
        """
        token doesn't match the format: ddmmyyyy
        """
        with pytest.raises(ValidationError) as err:
            syntax.SignedUserCreate(
                **{"email": "test@proquiz.com", "token": "02231970"}
            )
        assert err.value.errors()[0]["msg"] == "Invalid token format"
