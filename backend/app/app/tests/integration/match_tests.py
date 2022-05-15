from datetime import datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.domain_service.data_transfer.user import UserDTO
from app.tests.fixtures import TEST_1


class TestCaseBadRequest:
    def t_creation(self, client: TestClient, superuser_token_headers: dict) -> None:
        response = client.post(
            f"{settings.API_V1_STR}/matches/new",
            json={"questions": [None]},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def t_update(self, client: TestClient, superuser_token_headers: dict) -> None:
        response = client.put(
            f"{settings.API_V1_STR}/matches/edit/1",
            json={"questions": [1]},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCaseMatchEndpoints:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.reaction_dto = ReactionDTO(session=db_session)
        self.match_dto = MatchDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)

    def t_successfulCreationOfAMatch(
        self, client: TestClient, superuser_token_headers: dict
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

    def t_createMatchWithCode(self, client: TestClient, superuser_token_headers: dict):
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

    def t_requestUnexistentMatch(self, client: TestClient):
        response = client.get(f"{settings.API_V1_STR}/matches/30")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_retriveOneMatchWithAllData(self, client: TestClient):
        match_name = "New Match"
        match = self.match_dto.new(name=match_name)
        self.match_dto.save(match)
        first_game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(first_game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
        )
        self.question_dto.save(question)

        second_game = self.game_dto.new(match_uid=match.uid, index=1)
        self.game_dto.save(second_game)
        question = self.question_dto.new(
            text="Where is Vienna?",
            game_uid=second_game.uid,
            position=0,
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
        self, client: TestClient, superuser_token_headers: dict
    ):
        match_name = "New Match"
        match = self.match_dto.new(name=match_name)
        self.match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        self.question_dto.save(question)
        user = self.user_dto.new(email="t@t.com")
        self.user_dto.save(user)
        reaction = self.reaction_dto.new(match=match, question=question, user=user)
        self.reaction_dto.save(reaction)
        response = client.put(
            f"{settings.API_V1_STR}/matches/edit/{match.uid}",
            json={"times": 1, "name": match.name},
            headers=superuser_token_headers,
        )
        assert response.json()["error"] == "Match started. Cannot be edited"

    def t_addQuestionToExistingMatchWithOneGameOnly(
        self, client: TestClient, superuser_token_headers: dict
    ):
        match = self.match_dto.new()
        self.match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        self.question_dto.save(question)
        payload = {
            "times": 10,
            "questions": [
                {
                    "game": game.index,
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
        assert len(game.ordered_questions) == 2
        self.match_dto.refresh(match)
        assert match.times == 10

    def t_listAllMatches(self, client: TestClient):
        m1 = self.match_dto.save(self.match_dto.new())
        m2 = self.match_dto.save(self.match_dto.new())
        m3 = self.match_dto.save(self.match_dto.new())

        response = client.get(f"{settings.API_V1_STR}/matches/")
        assert response.json()["matches"] == [m.json for m in [m1, m2, m3]]

    def t_importQuestionsFromYaml(
        self, client: TestClient, superuser_token_headers: dict, yaml_file_handler
    ):
        match = self.match_dto.new()
        self.match_dto.save(match)
        base64_content, fname = yaml_file_handler
        superuser_token_headers.update(filename=fname)
        response = client.post(
            f"{settings.API_V1_STR}/matches/yaml_import",
            json={"uid": match.uid, "data": base64_content},
            headers=superuser_token_headers,
        )

        assert response.json()["questions_list"][0]["text"] == "What is your name?"
        assert response.json()["questions_list"][0]["answers_list"]
