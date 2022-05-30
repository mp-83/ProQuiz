import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.question import QuestionDTO


class TestCaseQuestionEP:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)

    def t_unexistentQuestion(self, client: TestClient):
        response = client.get(f"{settings.API_V1_STR}/questions/30")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_fetchingSingleQuestion(self, client: TestClient):
        question = self.question_dto.new(text="Text", position=0)
        self.question_dto.save(question)
        response = client.get(f"{settings.API_V1_STR}/questions/{question.uid}")
        assert response.ok
        assert response.json()["text"] == "Text"
        assert response.json()["answers_list"] == []

    def t_createNewQuestion(self, client: TestClient, superuser_token_headers: dict):
        # CSRF token is needed also in this case
        response = client.post(
            f"{settings.API_V1_STR}/questions/new",
            json={
                "text": "eleven pm",
                "position": 2,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert self.question_dto.count() == 1
        assert response.json()["text"] == "eleven pm"
        assert response.json()["position"] == 2

    def t_createNewQuestionWithContentUrl(
        self, client: TestClient, superuser_token_headers: dict
    ):
        # CSRF token is needed also in this case
        response = client.post(
            f"{settings.API_V1_STR}/questions/new",
            json={
                "content_url": "https://img.com",
                "position": 2,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert self.question_dto.count() == 1
        assert response.json()["text"] == "ContentURL"
        assert response.json()["content_url"] == "https://img.com"
        assert response.json()["position"] == 2

    def t_changeTextAndPositionOfAQuestion(
        self, client: TestClient, superuser_token_headers: dict
    ):
        question = self.question_dto.new(text="Text", position=0)
        self.question_dto.save(question)
        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={
                "text": "Edited text",
                "position": 2,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert response.json()["text"] == "Edited text"
        assert response.json()["position"] == 2

    def t_positionCannotBeNegative(
        self, client: TestClient, superuser_token_headers: dict
    ):
        question = self.question_dto.new(text="Text", position=0)
        self.question_dto.save(question)
        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={"position": -1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def t_changingContentUrlWithText(
        self, client: TestClient, superuser_token_headers: dict
    ):
        url = "https://img.org"
        question = self.question_dto.new(text="Text", position=0)
        self.question_dto.save(question)
        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={"text": None, "position": 1, "content_url": url},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["content_url"] == url
        assert response.json()["text"] == "ContentURL"

    def t_updateAnswerTextAndPosition(
        self, client: TestClient, superuser_token_headers: dict
    ):
        question = self.question_dto.new(text="new-question", position=0)
        self.question_dto.save(question)
        a1 = self.answer_dto.new(question_uid=question.uid, text="Answer1", position=0)
        self.answer_dto.save(a1)
        a2 = self.answer_dto.new(question_uid=question.uid, text="Answer2", position=1)
        self.answer_dto.save(a2)

        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={
                "answers": [
                    {
                        "uid": a2.uid,
                        "text": "changed answer 2 and moved it to pos 1",
                    },
                    {"uid": a1.uid, "text": a1.text},
                ]
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert question.answers_by_position[0].uid == a2.uid

    def t_listAllQuestions(
        self, client: TestClient, superuser_token_headers: dict, question_dto
    ):
        new_question = question_dto.new(text="First Question", position=1)
        question_dto.save(new_question)

        response = client.get(
            f"{settings.API_V1_STR}/questions/",
            headers=superuser_token_headers,
        )
        assert len(response.json()["questions"]) == 1
        questions_data = response.json()["questions"]
        assert questions_data[0]["text"] == "First Question"
