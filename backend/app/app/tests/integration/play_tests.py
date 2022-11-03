from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.domain_service.data_transfer.user import UserDTO, WordDigest


class TestCaseBadRequest:
    def test_endpoints(self, client: TestClient, superuser_token_headers: dict):
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
    def test_playLand(
        self, client: TestClient, superuser_token_headers: dict, db_session
    ):
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(with_code=False)
        match_dto.save(match)
        response = client.post(
            f"{settings.API_V1_STR}/play/h/{match.uhash}",
            json={},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["match_uid"] == match.uid


class TestCasePlayCode:
    def test_playCode(
        self, client: TestClient, superuser_token_headers: dict, db_session
    ):
        in_one_hour = datetime.now(tz=timezone.utc) + timedelta(hours=1)
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
        assert response.json()["match_uid"] == match.uid


class TestCasePlaySign:
    def test_successfulSignReturnsExisting(
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

    def test_unexistentMatch(self, client: TestClient, superuser_token_headers: dict):
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": 100, "user_uid": 1},
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_startExpiredMatch(self, client: TestClient, superuser_token_headers: dict):
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

    def test_startMatchAndUserIsImplicitlyCreated(
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
        assert response.json()["match_uid"] == match.uid
        assert response.json()["question"]["uid"] == question.uid
        assert response.json()["question"]["answers_to_display"] == []
        assert response.json()["attempt_uid"]
        assert response.json()["user_uid"]

    def test_startMatchWithoutQuestion(
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
    def test_startRestrictedMatchUsingPassword(
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
        assert response.json()["question"]["text"] == question.text
        assert response.json()["question"]["game"]["uid"] == game.uid
        assert response.json()["question"]["game"]["order"] == game.order
        assert response.json()["attempt_uid"]


class TestCasePlayNext:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)

    def test_duplicateSameReaction(
        self, client: TestClient, superuser_token_headers: dict, trivia_match
    ):
        match = trivia_match
        user = self.user_dto.fetch(signed=match.is_restricted)
        question = match.questions[0][0]
        answer = question.answers_by_position[0]

        client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        current_reaction = user.reactions.first()
        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
                "attempt_uid": current_reaction.attempt_uid,
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
                "attempt_uid": current_reaction.attempt_uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Duplicate Reactions"}

    def test_completeMixedMatch(
        self, client: TestClient, superuser_token_headers: dict, db_session
    ):
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(with_code=True)
        match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
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
        open_question = self.question_dto.new(
            text="Where is Dallas?",
            game_uid=game.uid,
            position=1,
            time=2,
        )
        self.question_dto.save(open_question)

        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        attempt_uid = response.json()["attempt_uid"]
        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
                "attempt_uid": attempt_uid,
            },
            headers=superuser_token_headers,
        )
        assert response.json()["question"]["answers_to_display"] == []

        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": open_question.uid,
                "open_answer_text": "Dallas is in Texas",
                "user_uid": user.uid,
                "attempt_uid": attempt_uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert response.json()["match_uid"] is None
        assert response.json()["score"] > 0
        assert match.rankings.count() == 1

    def test_continueStartedMatchWithMultipleGames(
        self, client: TestClient, superuser_token_headers: dict, db_session
    ):
        # first and only question of the first game is answered
        # first question of the second game is answered
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(with_code=True)
        match_dto.save(match)

        reaction_dto = ReactionDTO(session=db_session)

        first_game = self.game_dto.new(match_uid=match.uid, index=0, order=False)
        self.game_dto.save(first_game)
        first_question = self.question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
        )
        self.question_dto.save(first_question)
        first_answer = self.answer_dto.new(
            question=first_question, text="UK", position=1
        )
        self.answer_dto.save(first_answer)

        second_game = self.game_dto.new(match_uid=match.uid, index=1, order=False)
        self.game_dto.save(second_game)

        second_question = self.question_dto.new(
            text="Where is Paris?",
            game_uid=second_game.uid,
            position=1,
        )
        self.question_dto.save(second_question)

        third_question = self.question_dto.new(
            text="Where is Dublin?",
            game_uid=second_game.uid,
            position=2,
        )
        self.question_dto.save(third_question)
        third_answer = self.answer_dto.new(
            question=third_question, text="Ireland", position=1
        )
        self.answer_dto.save(third_answer)

        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        reaction_dto.save(
            reaction_dto.new(
                match_uid=match.uid,
                question_uid=first_question.uid,
                user_uid=user.uid,
                game_uid=first_game.uid,
                answer_uid=first_answer.uid,
                score=1,
            )
        )

        first_reaction = user.reactions.first()
        reaction_dto.save(
            reaction_dto.new(
                match=match,
                question=second_question,
                user=user,
                game_uid=second_game.uid,
                attempt_uid=first_reaction.attempt_uid,
                score=None,
            )
        )

        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": third_question.uid,
                "answer_uid": third_answer.uid,
                "user_uid": user.uid,
                "attempt_uid": first_reaction.attempt_uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert response.json()["match_uid"] is None
        assert match.rankings.count() == 1
        attempt_uid = user.reactions.first().attempt_uid
        assert user.reactions.filter_by(attempt_uid=attempt_uid).count() == 3

    def test_7(self, client: TestClient, superuser_token_headers: dict, db_session):
        """
        GIVEN: an existing match with one open question
        WHEN: it is answered
        THEN: then an OpenAnswer is created.
        """
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(with_code=True)
        match_dto.save(match)

        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=2,
        )
        self.question_dto.save(question)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        attempt_uid = response.json()["attempt_uid"]

        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": None,
                "answer_text": "London is in the United Kindom",
                "user_uid": user.uid,
                "attempt_uid": attempt_uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert response.json()["match_uid"] is None

        assert match.reactions.filter_by(open_answer_uid__isnot=None).count()
        # assert question.open_answers.first().text == "London is in the United Kingdom"
        assert match.rankings.count() == 1

    def test_8(self, client: TestClient, superuser_token_headers: dict, db_session):
        """
        GIVEN: a restricted match with two question that can be
                played unlimited times
        WHEN: the user plays two times
        THEN: the system should behave correctly, each time
        """
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(is_restricted=True, times=0)
        match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question_1 = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=None,
        )
        self.question_dto.save(question_1)
        answer_1 = self.answer_dto.new(
            question=question_1, text="UK", position=0, level=2
        )
        self.answer_dto.save(answer_1)

        question_2 = self.question_dto.new(
            text="Where is Tokyo?",
            game_uid=game.uid,
            position=1,
            time=None,
        )
        self.question_dto.save(question_2)
        answer_2 = self.answer_dto.new(
            question=question_2, text="Japan", position=0, level=2
        )
        self.answer_dto.save(answer_2)

        user = self.user_dto.fetch(signed=True)
        for _ in range(2):
            response = client.post(
                f"{settings.API_V1_STR}/play/start",
                json={
                    "match_uid": match.uid,
                    "user_uid": user.uid,
                    "password": match.password,
                },
                headers=superuser_token_headers,
            )
            assert response.ok
            attempt_uid = response.json()["attempt_uid"]

            client.post(
                f"{settings.API_V1_STR}/play/next",
                json={
                    "match_uid": match.uid,
                    "question_uid": question_1.uid,
                    "answer_uid": answer_1.uid,
                    "user_uid": user.uid,
                    "attempt_uid": attempt_uid,
                },
                headers=superuser_token_headers,
            )
            response = client.post(
                f"{settings.API_V1_STR}/play/next",
                json={
                    "match_uid": match.uid,
                    "question_uid": question_2.uid,
                    "answer_uid": answer_2.uid,
                    "user_uid": user.uid,
                    "attempt_uid": attempt_uid,
                },
                headers=superuser_token_headers,
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["question"] is None
            assert response.json()["match_uid"] is None
            assert response.json()["score"] > 0

        assert match.rankings.count() == 2

    def test_9(self, client: TestClient, superuser_token_headers: dict, db_session):
        """
        GIVEN: an existing match, not started via previous
                call to /next
        WHEN: the user sends a request to /next endpoint
        THEN: an error should be returned
        """
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(is_restricted=True, times=0)
        match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question_1 = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=None,
        )
        self.question_dto.save(question_1)
        user = self.user_dto.new(
            email="user@test.project",
        )
        self.user_dto.save(user)
        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question_1.uid,
                "answer_uid": None,
                "user_uid": user.uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_10(self, client: TestClient, superuser_token_headers: dict, db_session):
        """
        GIVEN: a restricted match with two question that can be
                played unlimited times
        WHEN: the user plays two times
        THEN: the system should behave correctly, each time
        """
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(is_restricted=True, times=1)
        match_dto.save(match)
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question_1 = self.question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=None,
        )
        self.question_dto.save(question_1)
        answer_1 = self.answer_dto.new(
            question=question_1, text="UK", position=0, level=2
        )
        self.answer_dto.save(answer_1)
        user = self.user_dto.fetch(signed=True)
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
                "password": match.password,
            },
            headers=superuser_token_headers,
        )
        assert response.ok
        attempt_uid = response.json()["attempt_uid"]

        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question_1.uid,
                "answer_uid": answer_1.uid,
                "user_uid": user.uid,
                "attempt_uid": attempt_uid,
            },
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert response.json()["match_uid"] is None
        assert response.json()["correct"]
        assert response.json()["score"] > 0
