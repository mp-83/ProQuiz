from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_entities import Answer, Game, Match, User
from app.domain_entities.user import UserFactory, WordDigest
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.ranking import RankingDTO


class TestCaseBadRequest:
    def t_endpoints(self, client: TestClient, superuser_token_headers: dict, dbsession):
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
    def t_playLand(self, client: TestClient, superuser_token_headers: dict, dbsession):
        match = Match(with_code=False, db_session=dbsession).save()
        response = client.post(
            f"{settings.API_V1_STR}/play/h/{match.uhash}",
            json={},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["match"] == match.uid


class TestCasePlayCode:
    def t_playCode(self, client: TestClient, superuser_token_headers: dict, dbsession):
        in_one_hour = datetime.now() + timedelta(hours=1)
        match = Match(with_code=True, expires=in_one_hour, db_session=dbsession).save()
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
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        Match(with_code=True, db_session=dbsession).save()
        email_digest = WordDigest("user@test.io").value()
        token_digest = WordDigest("01112021").value()
        email = f"{email_digest}@progame.io"
        user = User(
            email=email,
            email_digest=email_digest,
            token_digest=token_digest,
            db_session=dbsession,
        ).save()
        response = client.post(
            f"{settings.API_V1_STR}/play/sign",
            json={"email": "user@test.io", "token": "01112021"},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user"] == user.uid


class TestCasePlayStart:
    @pytest.fixture(autouse=True)
    def setUp(self, dbsession):
        self.question_dto = QuestionDTO(session=dbsession)

    def t_unexistentMatch(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": 100, "user_uid": 1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def t_startExpiredMatch(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        match = Match(expires=one_hour_ago, db_session=dbsession).save()
        user = UserFactory(signed=match.is_restricted, db_session=dbsession).fetch()
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid, "user_uid": user.uid},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def t_startMatchAndUserIsImplicitlyCreated(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match = Match(is_restricted=False, db_session=dbsession).save()
        game = Game(match_uid=match.uid, db_session=dbsession).save()
        question = self.question_dto.new(
            game_uid=game.uid, text="1+1 is = to", position=0, db_session=dbsession
        )
        self.question_dto.save(question)

        UserFactory(signed=match.is_restricted, db_session=dbsession).fetch()

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
        assert response.json()["user"]

    def t_startMatchWithoutQuestion(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match = Match(is_restricted=False, db_session=dbsession).save()
        game = Game(match_uid=match.uid, db_session=dbsession).save()
        user = UserFactory(signed=match.is_restricted, db_session=dbsession).fetch()

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid, "user_uid": user.uid},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == f"Game {game.uid} has no questions"

    # the password feature is tested more thoroughly in the logical tests
    def t_startRestrictedMatchUsingPassword(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match = Match(is_restricted=True, db_session=dbsession).save()
        game = Game(match_uid=match.uid, db_session=dbsession).save()
        question = self.question_dto.new(
            game_uid=game.uid, text="1+1 is = to", position=0, db_session=dbsession
        )
        self.question_dto.save(question)
        user = UserFactory(signed=match.is_restricted, db_session=dbsession).fetch()

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
    def setUp(self, dbsession):
        self.question_dto = QuestionDTO(session=dbsession)

    def t_duplicateSameReaction(
        self, client: TestClient, superuser_token_headers: dict, dbsession, trivia_match
    ):
        match = trivia_match
        user = UserFactory(signed=match.is_restricted, db_session=dbsession).fetch()
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

    def t_unexistentQuestion(
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
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
        self, client: TestClient, superuser_token_headers: dict, dbsession, trivia_match
    ):
        match = trivia_match
        user = UserFactory(signed=match.is_restricted, db_session=dbsession).fetch()
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
        self, client: TestClient, superuser_token_headers: dict, dbsession
    ):
        match = Match(db_session=dbsession).save()
        first_game = Game(match_uid=match.uid, index=0, db_session=dbsession).save()
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
            time=2,
            db_session=dbsession,
        )
        self.question_dto.save(question)
        answer = Answer(
            question=question, text="UK", position=1, level=2, db_session=dbsession
        ).save()
        user = User(email="user@test.project", db_session=dbsession).save()
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
        assert len(RankingDTO(session=dbsession).of_match(match.uid)) == 1
