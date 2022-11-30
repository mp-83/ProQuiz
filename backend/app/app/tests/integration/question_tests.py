from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings


class TestCaseQuestionEP:
    def test_1(self, client: TestClient):
        """
        GIVEN: the `id` of a question
        WHEN: the GET request is issued
        THEN: a 404 is returned if not found
        """
        question_id = 30
        response = client.get(f"{settings.API_V1_STR}/questions/{question_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_2(self, client: TestClient, question_dto):
        """retrieve one question"""
        question = question_dto.new(text="Text", position=0)
        question_dto.save(question)
        response = client.get(f"{settings.API_V1_STR}/questions/{question.uid}")
        assert response.ok
        assert response.json()["text"] == "Text"
        assert response.json()["answers_list"] == []

    def test_3(self, ase_client: TestClient, question_dto):
        """Create a question with the given data"""
        response = ase_client.post(
            f"{settings.API_V1_STR}/questions/new",
            json={
                "text": "eleven pm",
                "position": 2,
            },
        )
        assert response.ok
        assert question_dto.count() == 1
        assert response.json()["text"] == "eleven pm"
        assert response.json()["position"] == 2

    def test_4(self, ase_client: TestClient, question_dto):
        """Create a question at the given position with the provided content_url"""
        response = ase_client.post(
            f"{settings.API_V1_STR}/questions/new",
            json={
                "content_url": "https://img.com",
                "position": 2,
            },
        )
        assert response.ok
        assert question_dto.count() == 1
        assert response.json()["text"] == "ContentURL"
        assert response.json()["content_url"] == "https://img.com"
        assert response.json()["position"] == 2

    def test_5(self, ase_client: TestClient, question_dto):
        """Update the question's text and position"""
        question = question_dto.new(text="Text", position=0, time=10)
        question_dto.save(question)
        response = ase_client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={
                "text": "Edited text",
                "position": 2,
            },
        )
        assert response.ok
        assert response.json()["text"] == "Edited text"
        assert response.json()["position"] == 2
        assert response.json()["time"] == 10

    def test_6(self, ase_client: TestClient, question_dto):
        """When there is a validation error a 422 is returned"""
        question = question_dto.new(text="Text", position=0)
        question_dto.save(question)
        response = ase_client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={"position": -1},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_7(self, ase_client: TestClient, question_dto):
        """Update the text and position of a single question"""
        url = "https://img.org"
        question = question_dto.new(text="Text", position=0)
        question_dto.save(question)
        response = ase_client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={"text": None, "content_url": url},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["content_url"] == url
        assert response.json()["text"] == "ContentURL"
        assert response.json()["position"] == 0

    def test_8(
        self,
        ase_client: TestClient,
        question_dto,
        answer_dto,
    ):
        """
        GIVEN: a payload with an array of answers arranged in a different order
        WHEN: the PATCH request is issued
        THEN: the answers of the question are effectively reordered
        """
        question = question_dto.new(text="new-question", position=0)
        question_dto.save(question)
        a1 = answer_dto.new(question_uid=question.uid, text="Answer1", position=0)
        answer_dto.save(a1)
        a2 = answer_dto.new(question_uid=question.uid, text="Answer2", position=1)
        answer_dto.save(a2)
        a3 = answer_dto.new(question_uid=question.uid, text="Answer3", position=2)
        answer_dto.save(a3)

        response = ase_client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={
                "answers": [{"uid": a2.uid}, {"uid": a3.uid}, {"uid": a1.uid}],
                "reorder": True,
            },
        )
        assert response.ok
        assert question.answers_by_position[0].uid == a2.uid
        assert question.answers_by_position[1].uid == a3.uid
        assert question.answers_by_position[2].uid == a1.uid

    def test_9(
        self,
        ase_client: TestClient,
        question_dto,
        answer_dto,
    ):
        """Updated the text of one answer of one question of the match"""
        question = question_dto.new(text="new-question", position=0)
        question_dto.save(question)
        a1 = answer_dto.new(
            question_uid=question.uid, text="Answer1", position=0, level=1
        )
        answer_dto.save(a1)

        response = ase_client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={
                "answers": [
                    {"uid": a1.uid, "text": "updated text"},
                ]
            },
        )
        assert response.ok
        assert question.answers_by_position[0].text == "updated text"
        assert question.answers_by_position[0].level == 1

    def test_10(self, ase_client: TestClient, question_dto):
        """Listing all existing questions without filters"""
        new_question = question_dto.new(text="First Question", position=1)
        question_dto.save(new_question)

        response = ase_client.get(
            f"{settings.API_V1_STR}/questions/",
        )
        assert len(response.json()["questions"]) == 1
        questions_data = response.json()["questions"]
        assert questions_data[0]["text"] == "First Question"
