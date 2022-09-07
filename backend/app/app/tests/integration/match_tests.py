from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.ranking import RankingDTO
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
        now = datetime.now(tz=timezone.utc) + timedelta(hours=1)
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
        assert response.json()["expires"] == tomorrow.isoformat().replace("+00:00", "")

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
                "game": {"index": 0, "match_uid": 1, "order": True, "uid": 1},
            },
            {
                "uid": 2,
                "position": 0,
                "text": "Where is Vienna?",
                "time": None,
                "content_url": None,
                "answers_list": [],
                "game": {"index": 1, "match_uid": 1, "order": True, "uid": 2},
            },
        ]

    def t_updateFromTimeAndToTime(
        self, client: TestClient, superuser_token_headers: dict
    ):
        match = self.match_dto.new(is_restricted=True)
        self.match_dto.save(match)
        response = client.put(
            f"{settings.API_V1_STR}/matches/edit/{match.uid}",
            json={
                "from_time": "2022-01-01T00:00:01+00:00",
                "to_time": "2022-12-31T23:59:59+00:00",
            },
            headers=superuser_token_headers,
        )

        assert response.ok
        self.match_dto.refresh(match)
        assert match.from_time == datetime.fromisoformat("2022-01-01T00:00:01")
        assert match.to_time == datetime.fromisoformat("2022-12-31T23:59:59")
        assert match.order
        assert match.is_restricted

    def t_changeGamesOrder(self, client: TestClient, superuser_token_headers: dict):
        match = self.match_dto.new()
        self.match_dto.save(match)
        first_game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(first_game)
        response = client.put(
            f"{settings.API_V1_STR}/matches/edit/{match.uid}",
            json={"games": [{"uid": first_game.uid, "order": False}]},
            headers=superuser_token_headers,
        )

        assert response.ok
        assert response.json()["games_list"][0]["order"] is False
        self.game_dto.refresh(first_game)
        assert not first_game.order

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
                    "question_uid": question.uid,
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
        first_game_questions = match.questions[0]
        assert len(first_game_questions) == 2
        assert first_game_questions[1].text == "What is the capital of Sweden?"
        assert first_game_questions[1].answers_by_position[0].is_correct
        assert not first_game_questions[1].answers_by_position[1].is_correct
        assert not first_game_questions[1].answers_by_position[2].is_correct
        assert game.questions.count() == 2
        self.match_dto.refresh(match)
        assert match.times == 10

    def t_listAllMatches(self, client: TestClient):
        self.match_dto.save(self.match_dto.new())
        self.match_dto.save(self.match_dto.new())
        self.match_dto.save(self.match_dto.new())

        response = client.get(f"{settings.API_V1_STR}/matches/")
        assert response.ok
        assert len(response.json()["matches"]) == 3
        assert set(response.json()["matches"][0].keys()) == {
            "code",
            "expires",
            "from_time",
            "games_list",
            "is_restricted",
            "name",
            "order",
            "password",
            "questions_list",
            "times",
            "uhash",
            "uid",
        }

    def t_importQuestionsFromYaml(
        self, client: TestClient, superuser_token_headers: dict, yaml_file_handler
    ):
        match = self.match_dto.new()
        self.match_dto.save(match)
        game = self.game_dto.save(self.game_dto.new(match_uid=match.uid))
        base64_content, fname = yaml_file_handler
        superuser_token_headers.update(filename=fname)
        response = client.post(
            f"{settings.API_V1_STR}/matches/yaml_import",
            json={"uid": match.uid, "data": base64_content, "game_uid": game.uid},
            headers=superuser_token_headers,
        )

        assert response.json()["questions_list"][0]["text"] == "Where is Paris?"
        assert response.json()["questions_list"][0]["answers_list"][0]["is_correct"]
        assert (
            response.json()["questions_list"][0]["answers_list"][0]["text"] == "France"
        )
        assert response.json()["questions_list"][0]["time"] == 10

        assert response.json()["questions_list"][1]["text"] == "Where is Oslo?"
        assert (
            response.json()["questions_list"][1]["answers_list"][1]["text"] == "Sweden"
        )
        assert response.json()["questions_list"][1]["time"] is None

    def t_importTemplateQuestions(
        self, client: TestClient, superuser_token_headers: dict, question_dto
    ):
        """
        this test guarantees that question with open answers can be
        created/imported
        """
        match = self.match_dto.new()
        self.match_dto.save(match)
        new_game = self.game_dto.save(self.game_dto.new(match_uid=match.uid))
        new_objects = question_dto.add_many(
            objects=[
                question_dto.new(text="First Question", position=1),
                question_dto.new(text="Second Question", position=2),
                question_dto.new(text="Third Question", position=3),
            ]
        )
        response = client.post(
            f"{settings.API_V1_STR}/matches/import_questions",
            json={
                "uid": match.uid,
                "questions": [q.uid for q in new_objects],
                "game_uid": new_game.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        assert len(match.questions_list) == 3

    def t_matchRankings(self, client: TestClient, db_session, match_dto):
        match = match_dto.save(match_dto.new())
        user_1 = UserDTO(session=db_session).fetch()
        user_2 = UserDTO(session=db_session).fetch()

        rank_1 = RankingDTO(session=db_session).new(
            match_uid=match.uid, user_uid=user_1.uid, score=4.1
        )
        rank_2 = RankingDTO(session=db_session).new(
            match_uid=match.uid, user_uid=user_2.uid, score=4.2
        )

        RankingDTO(session=db_session).add_many([rank_1, rank_2])

        response = client.get(f"{settings.API_V1_STR}/matches/rankings/{match.uid}")

        assert response.ok
        assert response.json()["rankings"] == [
            {
                "user": {"name": user_1.name, "uid": user_1.uid},
                "score": rank_1.score,
                "uid": rank_1.uid,
            },
            {
                "user": {"name": user_2.name, "uid": user_2.uid},
                "score": rank_2.score,
                "uid": rank_2.uid,
            },
        ]
