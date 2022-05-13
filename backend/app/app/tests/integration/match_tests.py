from datetime import datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_entities import Game, Match, Reaction, User
from app.domain_service.data_transfer.question import QuestionDTO
from app.tests.fixtures import TEST_1


class TestCaseBadRequest:
    def t_creation(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ) -> None:
        response = client.post(
            f"{settings.API_V1_STR}/matches/new",
            json={"questions": [None]},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def t_update(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ) -> None:
        response = client.put(
            f"{settings.API_V1_STR}/matches/edit/1",
            json={"questions": [1]},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCaseMatchEndpoints:
    @pytest.fixture(autouse=True)
    def setUp(self, dbsession):
        self.question_dto = QuestionDTO(session=dbsession)

    def t_successfulCreationOfAMatch(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match_name = "New Match"
        response = client.post(
            f"{settings.API_V1_STR}/matches/new",
            json={"name": match_name, "questions": TEST_1, "is_restricted": "true"},
            headers=superuser_token_headers,
        )
        assert response.ok
        questions = response.json()["questions_list"]
        assert len(questions) == 4
        assert questions[0]["text"] == TEST_1[0]["text"]
        assert response.json()["is_restricted"]

    def t_createMatchWithCode(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match_name = "New Match"
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        response = client.post(
            f"{settings.API_V1_STR}/matches/new",
            json={
                "name": match_name,
                "with_code": "true",
                "from_time": now.isoformat(),
                "to_time": tomorrow.isoformat(),
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert response.json()["code"]
        assert response.json()["expires"] == tomorrow.isoformat()

    def t_requestUnexistentMatch(self, client: TestClient, dbsession):
        response = client.get(f"{settings.API_V1_STR}/matches/30")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_retriveOneMatchWithAllData(self, client: TestClient, dbsession):
        match_name = "New Match"
        match = Match(name=match_name, db_session=dbsession).save()
        first_game = Game(match_uid=match.uid, db_session=dbsession).save()
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)

        second_game = Game(match_uid=match.uid, index=1, db_session=dbsession).save()
        question = self.question_dto.new(
            text="Where is Vienna?",
            game_uid=second_game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)

        response = client.get(f"{settings.API_V1_STR}/matches/{match.uid}")
        assert response.ok
        rjson = response.json()
        assert rjson["name"] == match_name
        assert rjson["questions_list"] == [
            {
                "uid": 1,
                "position": 0,
                "text": "Where is London?",
                "time": None,
                "content_url": None,
                "answers_list": [],
            },
            {
                "uid": 2,
                "position": 0,
                "text": "Where is Vienna?",
                "time": None,
                "content_url": None,
                "answers_list": [],
            },
        ]

    def t_matchCannotBeChangedIfStarted(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match_name = "New Match"
        match = Match(name=match_name, db_session=dbsession).save()
        first_game = Game(match_uid=match.uid, db_session=dbsession).save()
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        user = User(email="t@t.com", db_session=dbsession).save()
        Reaction(match=match, question=question, user=user, db_session=dbsession).save()
        response = client.put(
            f"{settings.API_V1_STR}/matches/edit/{match.uid}",
            json={"times": 1, "name": match.name},
            headers=superuser_token_headers,
        )
        assert response.json()["error"] == "Match started. Cannot be edited"

    def t_addQuestionToExistingMatchWithOneGameOnly(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match = Match(db_session=dbsession).save()
        first_game = Game(match_uid=match.uid, db_session=dbsession).save()
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        payload = {
            "times": 10,
            "questions": [
                {
                    "game": first_game.index,
                    "text": "What is the capital of Sweden?",
                    "answers": [
                        {"text": "Stockolm"},
                        {"text": "Oslo"},
                        {"text": "London"},
                    ],
                }
            ],
        }
        response = client.put(
            f"{settings.API_V1_STR}/matches/edit/{match.uid}",
            json=payload,
            headers=superuser_token_headers,
        )
        assert response.ok
        assert len(match.questions[0]) == 2
        assert len(first_game.ordered_questions) == 2
        match.refresh()
        assert match.times == 10

    def t_listAllMatches(self, client: TestClient, dbsession):
        m1 = Match(db_session=dbsession).save()
        m2 = Match(db_session=dbsession).save()
        m3 = Match(db_session=dbsession).save()

        response = client.get(f"{settings.API_V1_STR}/matches/")
        assert response.json()["matches"] == [m.json for m in [m1, m2, m3]]

    def t_importQuestionsFromYaml(
        self,
        client: TestClient,
        superuser_token_headers: dict,
        yaml_file_handler,
        dbsession,
    ):
        match = Match(db_session=dbsession).save()
        base64_content, fname = yaml_file_handler
        superuser_token_headers.update(filename=fname)
        response = client.post(
            f"{settings.API_V1_STR}/matches/yaml_import",
            json={"uid": match.uid, "data": base64_content},
            headers=superuser_token_headers,
        )

        assert response.json()["questions_list"][0]["text"] == "What is your name?"
        assert response.json()["questions_list"][0]["answers_list"]
