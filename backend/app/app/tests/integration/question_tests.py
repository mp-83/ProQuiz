from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.entities import Answer, Question, Questions


class TestCaseQuestionEP:
    def t_unexistentQuestion(self, client: TestClient, dbsession):
        response = client.get(f"{settings.API_V1_STR}/questions/30")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_fetchingSingleQuestion(self, client: TestClient, dbsession):
        question = Question(text="Text", position=0, db_session=dbsession).save()
        response = client.get(f"{settings.API_V1_STR}/questions/{question.uid}")
        assert response.ok
        assert response.json()["text"] == "Text"
        assert response.json()["answers_list"] == []

    def t_createNewQuestion(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
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
        assert Questions(db_session=dbsession).count() == 1
        assert response.json()["text"] == "eleven pm"
        assert response.json()["position"] == 2

    def t_invalidText(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        response = client.post(
            f"{settings.API_V1_STR}/questions/new",
            json={"text": None, "position": 1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def t_changeTextAndPositionOfAQuestion(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        question = Question(text="Text", position=0, db_session=dbsession).save()
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
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        question = Question(text="Text", position=0, db_session=dbsession).save()
        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/{question.uid}",
            json={"position": -1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def t_editingUnexistentQuestion(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        response = client.put(
            f"{settings.API_V1_STR}/questions/edit/40",
            json={"text": "text", "position": 1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_updateAnswerTextAndPosition(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        question = Question(
            text="new-question", position=0, db_session=dbsession
        ).save()
        a1 = Answer(
            question_uid=question.uid, text="Answer1", position=0, db_session=dbsession
        ).save()
        a2 = Answer(
            question_uid=question.uid, text="Answer2", position=1, db_session=dbsession
        ).save()

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
