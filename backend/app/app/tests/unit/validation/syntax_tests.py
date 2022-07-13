from base64 import b64encode
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain_service.schemas import syntax_validation as syntax


class TestCaseNullable:
    def t_nullableValues(self):
        for schema, field in [
            (syntax.LandPlay, "match_uhash"),
            (syntax.CodePlay, "match_code"),
        ]:
            try:
                schema(**{field: None})
            except ValidationError as err:
                assert err.errors()[0]["msg"] == "none is not an allowed value"


class TestCasePlaySchemas:
    def t_matchUHashDoesNotMatchRegex(self):
        value = "IJD34KOP"
        try:
            syntax.LandPlay(**{"match_uhash": value})
        except ValidationError as err:
            assert err.errors()[0]["msg"] == f"uHash {value} does not match regex"

    def t_matchWrongCode(self):
        value = "34569"
        try:
            syntax.CodePlay(**{"match_code": value})
        except ValidationError as err:
            assert err.errors()[0]["msg"] == f"Code {value} does not match regex"

    def t_validStartPayloadWithoutUser(self):
        assert syntax.StartPlay(**{"match_uid": 1})

    def t_validStartPayloadWithoutPassword(self):
        assert syntax.StartPlay(**{"match_uid": 1, "user_uid": 1})

    def t_startPayloadWithInvalidPassword(self):
        password = "IJD34KOP"
        try:
            syntax.StartPlay(**{"match_uid": 1, "user_uid": 1, "password": password})
        except ValidationError as err:
            assert err.errors()[0]["msg"] == f"Password {password} does not match regex"

    def t_validStartPayloadWithValidPassword(self):
        schema = syntax.StartPlay(
            **{"match_uid": 1, "user_uid": 1, "password": "04542"}
        )
        assert schema.dict()["password"] == "04542"

    def t_validNextPayload(self):
        assert syntax.NextPlay(
            **{"match_uid": 1, "user_uid": 2, "answer_uid": 3, "question_uid": 4}
        )

    def t_allRequiredByDefault(self):
        try:
            syntax.NextPlay(**{"match_uid": 1, "user_uid": 2, "answer_uid": 3})
        except ValidationError as err:
            assert err.errors()[0]["loc"] == ("question_uid",)
            assert err.errors()[0]["msg"] == "field required"

    def t_emailAndBirthDate(self):
        assert syntax.SignPlay(**{"email": "user@pp.com", "token": "12022021"})

    def t_invalidBirthDateNull(self):
        try:
            syntax.SignPlay(**{"email": "user@pp.com", "token": None})
        except ValidationError as err:
            assert err.errors()[0]["loc"] == ("token",)
            assert err.errors()[0]["msg"] == "none is not an allowed value"

    def t_invalidEmailNull(self):
        try:
            syntax.SignPlay(**{"email": None, "token": "11012014"})
        except ValidationError as err:
            assert err.errors()[0]["loc"] == ("email",)
            assert err.errors()[0]["msg"] == "none is not an allowed value"


class TestCaseQuestionSchema:
    def t_textMaxLength(self):
        pytest.raises(
            ValidationError,
            syntax.QuestionCreate,
            **{"text": "".join("a" for _ in range(501)), "position": 1},
        )

    def t_textMinLength(self):
        pytest.raises(ValidationError, syntax.QuestionCreate, text="aa", position=1)

    def t_nullTextIsValid(self):
        assert syntax.QuestionCreate(text=None, position=1)

    def t_nullContentUrlIsValid(self):
        assert syntax.QuestionCreate(content_url=None)

    def t_urlMinLength(self):
        pytest.raises(
            ValidationError, syntax.QuestionCreate, content_url="aa", position=1
        )


class TestCaseMatchSchema:
    def t_createPayloadWithQuestions(self):
        schema = syntax.MatchCreate(
            **{
                "name": "new match",
                "times": "2",
                "is_restricted": "true",
                "questions": [
                    {
                        "text": "Which of the following statements cannot be inferred from the passage?",
                        "answers": [
                            {
                                "text": "The Turk began its tour of Europe in April of 1783."
                            },
                            {
                                "text": "Philidor found his match with the Turk challenging."
                            },
                        ],
                    },
                ],
            }
        )
        assert schema
        assert schema.dict()["is_restricted"] is True

    def t_expirationValuesCannotBeNone(self):
        try:
            syntax.MatchCreate(
                **{
                    "name": "new match",
                    "with_code": "true",
                    "questions": [],
                    "to_time": None,
                    "from_time": None,
                }
            )
        except ValidationError as err:
            assert err.errors()[0]["loc"] == ("from_time",)
            assert err.errors()[0]["msg"] == "none is not an allowed value"
            assert err.errors()[1]["loc"] == ("to_time",)
            assert err.errors()[1]["msg"] == "none is not an allowed value"

    def t_expirationValuesMustBeDatetimeIsoFormatted(self):
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

    def t_multipleEdgeValues(self):
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

    def t_partialPayloadValidation(self):
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
            - Where is Adelaide?
            - answers:
              - Australia
              - Japan
              - Kenya
            - Where is Paris
            - answers:
               - France
               - Argentina
               - Iceland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"
        yield b64string

    def t_validYamlContent(self, valid_encoded_yaml_content):
        schema = syntax.MatchYamlImport(
            **{"uid": 1, "data": valid_encoded_yaml_content}
        )
        assert schema
        assert schema.dict() == {
            "uid": 1,
            "data": {
                "questions": [
                    {
                        "text": "Where is Adelaide?",
                        "position": None,
                        "time": None,
                        "content_url": None,
                        "game": None,
                        "answers": [
                            {
                                "text": "Australia",
                                "uid": None,
                                "question_uid": None,
                                "position": None,
                                "level": None,
                                "is_correct": None,
                                "content_url": None,
                            },
                            {
                                "text": "Japan",
                                "uid": None,
                                "question_uid": None,
                                "position": None,
                                "level": None,
                                "is_correct": None,
                                "content_url": None,
                            },
                            {
                                "text": "Kenya",
                                "uid": None,
                                "question_uid": None,
                                "position": None,
                                "level": None,
                                "is_correct": None,
                                "content_url": None,
                            },
                        ],
                    },
                    {
                        "text": "Where is Paris",
                        "position": None,
                        "time": None,
                        "content_url": None,
                        "game": None,
                        "answers": [
                            {
                                "text": "France",
                                "uid": None,
                                "question_uid": None,
                                "position": None,
                                "level": None,
                                "is_correct": None,
                                "content_url": None,
                            },
                            {
                                "text": "Argentina",
                                "uid": None,
                                "question_uid": None,
                                "position": None,
                                "level": None,
                                "is_correct": None,
                                "content_url": None,
                            },
                            {
                                "text": "Iceland",
                                "uid": None,
                                "question_uid": None,
                                "position": None,
                                "level": None,
                                "is_correct": None,
                                "content_url": None,
                            },
                        ],
                    },
                ]
            },
        }

    def t_invalidYamlContent(self):
        # missing dash char before answers key
        document = """
          questions:
            - Where is Belfast?
            answers:
              - Sweden
              - England
              - Ireland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        try:
            syntax.MatchYamlImport(**{"uid": 1, "data": b64string})
        except ValidationError as err:
            assert err.errors()[0]["msg"] == "Content cannot be coerced"

    def t_invalidContentPadding(self, valid_encoded_yaml_content):
        try:
            syntax.MatchYamlImport(
                **{"uid": 1, "data": valid_encoded_yaml_content[:-1]}
            )
        except ValidationError as err:
            assert err.errors()[0]["msg"] == "Incorrect padding"

    def t_questionEmptyTextIsParseAsNull(self):
        document = """
          questions:
            -
            - answers:
              - Sweden
              - England
              - Ireland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        try:
            syntax.MatchYamlImport(**{"uid": 1, "data": b64string})
        except ValidationError as err:
            assert err.errors()[0]["loc"] == ("data", "questions", 0, "text")
            assert err.errors()[0]["msg"] == "none is not an allowed value"

    def t_questionIsMissingAnswersAreNotParsed(self):
        document = """
          questions:
            - answers:
              - Sweden
              - England
              - Ireland
        """
        b64content = b64encode(document.encode("utf-8")).decode()
        b64string = f"data:application/x-yaml;base64,{b64content}"

        schema = syntax.MatchYamlImport(**{"uid": 1, "data": b64string})
        assert schema
        assert schema.dict() == {"uid": 1, "data": {"questions": []}}

    def t_expectedMappingMethod(self):
        # test meant to document input => output transformation
        value = {
            "questions": [
                None,
                {"answers": ["Australia", "Japan", "Kenya"]},
                "Where is Paris",
                {"answers": ["France", "Argentina", "Iceland"]},
            ]
        }

        result = syntax.MatchYamlImport.to_expected_mapping(value)
        assert result == {
            "questions": [
                {
                    "text": None,
                    "answers": [
                        {"text": "Australia"},
                        {"text": "Japan"},
                        {"text": "Kenya"},
                    ],
                },
                {
                    "text": "Where is Paris",
                    "answers": [
                        {"text": "France"},
                        {"text": "Argentina"},
                        {"text": "Iceland"},
                    ],
                },
            ]
        }


class TestCaseUserSchema:
    def t_emptyUserNameAndPassword(self):
        # arguments are too short
        # is_valid = syntax_validation({"email": "", "password": "pass"})
        # assert not is_valid
        pass

    def t_invalidEmail(self):
        # is_valid = v.validate({"email": "e@a.c", "password": "password"})
        # assert not is_valid
        pass
