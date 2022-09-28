import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.question import QuestionDTO


class TestCaseQuestionEP:
    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)

    def test_1(self, client: TestClient):
        """
        GIVEN: the id of a question
        WHEN: the GET request is made
        THEN: a NOT-FOUND is returned if
        """
        question_id = 30
        response = client.get(f"{settings.API_V1_STR}/questions/{question_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_2(self, client: TestClient):
        """
        GIVEN: the id of an existing question
        WHEN: the GET request is issued
        THEN: the response should contain the question's data
        """
        question = self.question_dto.new(text="Text", position=0)
        self.question_dto.save(question)
        response = client.get(f"{settings.API_V1_STR}/questions/{question.uid}")
        assert response.ok
        assert response.json()["text"] == "Text"
        assert response.json()["answers_list"] == []

    def test_3(self, client: TestClient, superuser_token_headers: dict):
        """
        GIVEN: a payload with text and position
        WHEN: the POST request is made to the /new endpoint
        THEN: the object is created and the response contains
                the question's data
        """
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

    def test_4(self, client: TestClient, superuser_token_headers: dict):
        """
        GIVEN: a payload with position and contentURL instead of text
        WHEN: the POST request is made to the /new endpoint
        THEN: the object is created and the response contains
                the question's data
        """
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

    def test_5(self, client: TestClient, superuser_token_headers: dict):
        """
        GIVEN: a payload with a changed text and position
        WHEN: the PATCH request is made
        THEN: the question is updated
        """
        question = self.question_dto.new(text="Text", position=0, time=10)
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
        assert response.json()["time"] == 10

    def test_6(self, client: TestClient, superuser_token_headers: dict):
        """
        GIVEN: a payload with changed text and position
        WHEN: the PATCH request is made
        THEN: the question is updated
        """
        question = self.question_dto.new(text="Text", position=0)
        self.question_dto.save(question)
        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={"position": -1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_7(self, client: TestClient, superuser_token_headers: dict):
        """
        GIVEN: a payload with NULL text and a new content_url
        WHEN: the PATCH request is made
        THEN: the text is replaced with the content_url
        """
        url = "https://img.org"
        question = self.question_dto.new(text="Text", position=0)
        self.question_dto.save(question)
        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={"text": None, "content_url": url},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["content_url"] == url
        assert response.json()["text"] == "ContentURL"
        assert response.json()["position"] == 0

    def test_8(self, client: TestClient, superuser_token_headers: dict):
        """
        GIVEN: a payload with an array of answers with a new order
        WHEN: the PATCH request is made to the question.edit endpoint
        THEN: the question's answers are reordered
        """
        question = self.question_dto.new(text="new-question", position=0)
        self.question_dto.save(question)
        a1 = self.answer_dto.new(question_uid=question.uid, text="Answer1", position=0)
        self.answer_dto.save(a1)
        a2 = self.answer_dto.new(question_uid=question.uid, text="Answer2", position=1)
        self.answer_dto.save(a2)
        a3 = self.answer_dto.new(question_uid=question.uid, text="Answer3", position=2)
        self.answer_dto.save(a3)

        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={
                "answers": [{"uid": a2.uid}, {"uid": a3.uid}, {"uid": a1.uid}],
                "reorder": True,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert question.answers_by_position[0].uid == a2.uid
        assert question.answers_by_position[1].uid == a3.uid
        assert question.answers_by_position[2].uid == a1.uid

    def test_9(self, client: TestClient, superuser_token_headers: dict):
        """
        GIVEN: a payload with the text of an answer changed
        WHEN: the PATCH request is issued to the question.edit
        THEN: the text of the answer is updated
        """
        question = self.question_dto.new(text="new-question", position=0)
        self.question_dto.save(question)
        a1 = self.answer_dto.new(
            question_uid=question.uid, text="Answer1", position=0, level=1
        )
        self.answer_dto.save(a1)

        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={
                "answers": [
                    {"uid": a1.uid, "text": "updated text"},
                ]
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert question.answers_by_position[0].text == "updated text"
        assert question.answers_by_position[0].level == 1

    def test_10(self, client: TestClient, superuser_token_headers: dict, question_dto):
        """
        GIVEN: a set of existing questions
        WHEN: a GET request is made to the /questions endpoint
        THEN: all the records are returned
        """
        new_question = question_dto.new(text="First Question", position=1)
        question_dto.save(new_question)

        response = client.get(
            f"{settings.API_V1_STR}/questions/",
            headers=superuser_token_headers,
        )
        assert len(response.json()["questions"]) == 1
        questions_data = response.json()["questions"]
        assert questions_data[0]["text"] == "First Question"
