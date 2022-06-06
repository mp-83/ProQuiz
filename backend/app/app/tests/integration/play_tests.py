from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.ranking import RankingDTO
from app.domain_service.data_transfer.user import UserDTO, WordDigest


class TestCaseBadRequest:
    def t_endpoints(self, client: TestClient, superuser_token_headers: dict):
        endpoints = ["/play/h/BAD", "/play/start", "/play/next", "/play/sign"]
        for endpoint in endpoints:
            response = client.post(
                f"{settings.API_V1_STR}{endpoint}",
                json={"questions": [None]},
                headers=superuser_token_headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCasePlayLand:
    # the test scenario for land/404 is already tested above
    def t_playLand(self, client: TestClient, superuser_token_headers: dict, db_session):
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(with_code=False)
        match_dto.save(match)
        response = client.post(
            f"{settings.API_V1_STR}/play/h/{match.uhash}",
            json={},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["match"] == match.uid


class TestCasePlayCode:
    def t_playCode(self, client: TestClient, superuser_token_headers: dict, db_session):
        in_one_hour = datetime.now() + timedelta(hours=1)
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(with_code=True, expires=in_one_hour)
        match_dto.save(match)
        response = client.post(
            f"{settings.API_V1_STR}/play/code",
            json={"match_code": match.code},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        # the user.uid value can't be known ahead, but it will be > 0
        assert response.json()["user"]
        assert response.json()["match"] == match.uid


class TestCasePlaySign:
    def t_successfulSignReturnsExisting(
        self, client: TestClient, superuser_token_headers: dict, match_dto, user_dto
    ):
        match = match_dto.new(with_code=True)
        match_dto.save(match)
        email_digest = WordDigest("user@test.io").value()
        token_digest = WordDigest("01112021").value()
        email = f"{email_digest}@progame.io"
        user = user_dto.new(
            email=email,
            email_digest=email_digest,
            token_digest=token_digest,
        )
        user_dto.save(user)
        response = client.post(
            f"{settings.API_V1_STR}/play/sign",
            json={"email": "user@test.io", "token": "01112021"},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user"] == user.uid


class TestCasePlayStart:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.match_dto = MatchDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)

    def t_unexistentMatch(self, client: TestClient, superuser_token_headers: dict):
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": 100, "user_uid": 1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_startExpiredMatch(self, client: TestClient, superuser_token_headers: dict):
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        match = self.match_dto.new(expires=one_hour_ago)
        self.match_dto.save(match)

        user = self.user_dto.fetch(signed=match.is_restricted)
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid, "user_uid": user.uid},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def t_startMatchAndUserIsImplicitlyCreated(
        self, client: TestClient, superuser_token_headers: dict
    ):
        match = self.match_dto.new(is_restricted=False)
        self.match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            game_uid=game.uid, text="1+1 is = to", position=0
        )
        self.question_dto.save(question)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid},
            headers=superuser_token_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["match"] == match.uid
        assert response.json()["question"] == question.json
        assert response.json()["question"]["answers"] == []
        # the user.uid value can't be known ahead, but it will be > 0
        assert response.json()["user"] > 0

    def t_startMatchWithoutQuestion(
        self, client: TestClient, superuser_token_headers: dict
    ):
        match = self.match_dto.new(is_restricted=False)
        self.match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        user = self.user_dto.fetch(signed=match.is_restricted)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid, "user_uid": user.uid},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == f"Game {game.uid} has no questions"

    # the password feature is tested more thoroughly in the logical_validation tests
    def t_startRestrictedMatchUsingPassword(
        self, client: TestClient, superuser_token_headers: dict
    ):
        match = self.match_dto.new(is_restricted=True)
        self.match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            game_uid=game.uid, text="1+1 is = to", position=0
        )
        self.question_dto.save(question)
        user = self.user_dto.fetch(signed=match.is_restricted)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
                "password": match.password,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] == question.json


class TestCasePlayNext:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)

    def t_duplicateSameReaction(
        self, client: TestClient, superuser_token_headers: dict, trivia_match
    ):
        match = trivia_match
        user = self.user_dto.fetch(signed=match.is_restricted)
        question = match.questions[0][0]
        answer = question.answers_by_position[0]

        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def t_unexistentQuestion(self, client: TestClient, superuser_token_headers: dict):
        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": 1,
                "question_uid": 1,
                "answer_uid": 1,
                "user_uid": 1,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_answerQuestion(
        self, client: TestClient, superuser_token_headers: dict, trivia_match
    ):
        match = trivia_match
        user = self.user_dto.fetch(signed=match.is_restricted)
        question = match.questions[0][0]
        answer = question.answers_by_position[0]

        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] == match.questions[0][1].json
        assert response.json()["user"] == user.uid

    def t_completeMatch(
        self, client: TestClient, superuser_token_headers: dict, db_session
    ):
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(with_code=True)
        match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid, index=0)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=2,
        )
        self.question_dto.save(question)
        answer = self.answer_dto.new(question=question, text="UK", position=1, level=2)
        self.answer_dto.save(answer)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert len(RankingDTO(session=db_session).of_match(match.uid)) == 1
