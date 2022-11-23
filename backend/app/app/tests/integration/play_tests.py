from datetime import datetime, timedelta, timezone

from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain_service.data_transfer.user import WordDigest


class TestCaseBadRequest:
    def test_1(self, client: TestClient, superuser_token_headers: dict):
        """Tests some edge cases"""
        endpoints = ["/play/h/BAD", "/play/start", "/play/next", "/play/sign"]
        for endpoint in endpoints:
            response = client.post(
                f"{settings.API_V1_STR}{endpoint}",
                json={"questions": [None]},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCasePlayLand:
    def test_1(self, client: TestClient, match_dto):
        """verify the match.uid is returned, when playing a match with hash"""
        match = match_dto.new(with_code=False)
        match_dto.save(match)
        response = client.post(
            f"{settings.API_V1_STR}/play/h/{match.uhash}",
            json={},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["match_uid"] == match.uid


class TestCasePlayCode:
    def test_1(self, client: TestClient, db_session, match_dto):
        """verify the match.uid and user are returned, when
        playing a match with code
        """
        in_one_hour = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        match = match_dto.new(with_code=True, expires=in_one_hour)
        match_dto.save(match)
        response = client.post(
            f"{settings.API_V1_STR}/play/code",
            json={"match_code": match.code},
        )
        assert response.status_code == status.HTTP_200_OK
        # the user.uid value can't be known ahead, but it will be > 0
        assert response.json()["user"]
        assert response.json()["match_uid"] == match.uid


class TestCasePlaySign:
    def test_1(self, client: TestClient, match_dto, user_dto):
        """
        GIVEN: an existing user
        WHEN: the user successfully signs in/logs in
        THEN: the user is returned in the response
        """
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
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user"] == user.uid


class TestCasePlayStart:
    def test_1(self, client: TestClient):
        """Start unexistent match"""
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": 100, "user_uid": 1},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_2(self, client: TestClient, match_dto, user_dto):
        """Start a match that has already expired"""
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        match = match_dto.new(expires=one_hour_ago)
        match_dto.save(match)

        user = user_dto.fetch(signed=match.is_restricted)
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid, "user_uid": user.uid},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_3(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        question_dto,
    ):
        """
        GIVEN: an existing match
        WHEN: it is started without providing the user parameter
        THEN: the user is created internally and returned in the response
        """
        match = match_dto.new(is_restricted=False)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(game_uid=game.uid, text="1+1 is = to", position=0)
        question_dto.save(question)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["match_uid"] == match.uid
        assert response.json()["question"]["uid"] == question.uid
        assert response.json()["question"]["answers_to_display"] == []
        assert response.json()["attempt_uid"]
        assert response.json()["user_uid"]

    def test_4(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        user_dto,
    ):
        """Starting a match without questions"""
        match = match_dto.new(is_restricted=False)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        user = user_dto.fetch(signed=match.is_restricted)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={"match_uid": match.uid, "user_uid": user.uid},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == f"Game {game.uid} has no questions"

    def test_5(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        question_dto,
        user_dto,
    ):
        """Start a restricte match also passing the password in the payload"""
        match = match_dto.new(is_restricted=True)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(game_uid=game.uid, text="1+1 is = to", position=0)
        question_dto.save(question)
        user = user_dto.fetch(signed=match.is_restricted)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
                "password": match.password,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"]["text"] == question.text
        assert response.json()["question"]["game"]["uid"] == game.uid
        assert response.json()["question"]["game"]["order"] == game.order
        assert response.json()["attempt_uid"]


class TestCasePlayNext:
    def test_1(self, client: TestClient, trivia_match, user_dto):
        """
        GIVEN: an existing match with several question
        WHEN: the user submits the same reaction twice
        THEN: an error should be returned
        """
        match = trivia_match
        user = user_dto.fetch(signed=match.is_restricted)
        question = match.questions[0][0]
        answer = question.answers_by_position[0]

        client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
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
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Duplicate Reactions"}

    def test_2(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        question_dto,
        answer_dto,
        user_dto,
    ):
        """Play a whole match, made of a question and one open-question"""
        match = match_dto.new(with_code=True, notify_correct=True)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=2,
        )
        question_dto.save(question)
        answer = answer_dto.new(question=question, text="UK", position=1, level=2)
        answer_dto.save(answer)
        open_question = question_dto.new(
            text="Where is Dallas?",
            game_uid=game.uid,
            position=1,
            time=2,
        )
        question_dto.save(open_question)

        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
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
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert "match_uid" not in response.json()
        assert response.json()["score"] > 0
        assert response.json()["was_correct"] is False
        assert match.rankings.count() == 1

    def test_3(
        self,
        client: TestClient,
        match_dto,
        reaction_dto,
        game_dto,
        question_dto,
        answer_dto,
        user_dto,
    ):
        """
        GIVEN: a multi-games match that was already started
                (there are already existing reactions)
        WHEN: the user start playing again
        THEN: the execution should continue from where it was left
        """
        match = match_dto.new(with_code=True, notify_correct=True)
        match_dto.save(match)

        first_game = game_dto.new(match_uid=match.uid, index=0, order=False)
        game_dto.save(first_game)
        first_question = question_dto.new(
            text="Where is London?",
            game_uid=first_game.uid,
            position=0,
        )
        question_dto.save(first_question)
        first_answer = answer_dto.new(question=first_question, text="UK", position=0)
        answer_dto.save(first_answer)

        second_game = game_dto.new(match_uid=match.uid, index=1, order=False)
        game_dto.save(second_game)

        second_question = question_dto.new(
            text="Where is Paris?",
            game_uid=second_game.uid,
            position=1,
        )
        question_dto.save(second_question)

        third_question = question_dto.new(
            text="Where is Dublin?",
            game_uid=second_game.uid,
            position=2,
        )
        question_dto.save(third_question)
        third_answer = answer_dto.new(
            question=third_question, text="Ireland", position=0
        )
        answer_dto.save(third_answer)

        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

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
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert response.json()["was_correct"]
        assert match.rankings.count() == 1
        attempt_uid = user.reactions.first().attempt_uid
        assert user.reactions.filter_by(attempt_uid=attempt_uid).count() == 3

    def test_4(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        question_dto,
        user_dto,
    ):
        """
        GIVEN: an existing match with one open question
        WHEN: it is answered
        THEN: then an OpenAnswer is created.
        """
        match = match_dto.new(with_code=True)
        match_dto.save(match)

        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=2,
        )
        question_dto.save(question)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
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
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert response.json()["was_correct"] is None

        assert match.reactions.filter_by(open_answer_uid__isnot=None).count()
        assert match.rankings.count() == 1

    def test_5(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        question_dto,
        answer_dto,
        user_dto,
    ):
        """
        GIVEN: a restricted match with two question that can be
                played unlimited times
        WHEN: the user plays two times
        THEN: the system should behave correctly, each time
        """
        match = match_dto.new(is_restricted=True, times=0)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question_1 = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=None,
        )
        question_dto.save(question_1)
        answer_1 = answer_dto.new(question=question_1, text="UK", position=0, level=2)
        answer_dto.save(answer_1)

        question_2 = question_dto.new(
            text="Where is Tokyo?",
            game_uid=game.uid,
            position=1,
            time=None,
        )
        question_dto.save(question_2)
        answer_2 = answer_dto.new(
            question=question_2, text="Japan", position=0, level=2
        )
        answer_dto.save(answer_2)

        user = user_dto.fetch(signed=True)
        for _ in range(2):
            response = client.post(
                f"{settings.API_V1_STR}/play/start",
                json={
                    "match_uid": match.uid,
                    "user_uid": user.uid,
                    "password": match.password,
                },
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
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["question"] is None
            assert response.json()["score"] > 0
            assert response.json()["was_correct"] is None

        assert match.rankings.count() == 2

    def test_6(
        self,
        client: TestClient,
        match_dto,
        game_dto,
        user_dto,
        question_dto,
    ):
        """
        GIVEN: an existing match, not started via previous
                call to /next
        WHEN: the user sends a request to /next endpoint
        THEN: an error should be returned
        """
        match = match_dto.new(is_restricted=True, times=0)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question_1 = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=None,
        )
        question_dto.save(question_1)
        user = user_dto.new(
            email="user@test.project",
        )
        user_dto.save(user)
        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": question_1.uid,
                "answer_uid": None,
                "user_uid": user.uid,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_7(
        self,
        client: TestClient,
        match_dto,
        user_dto,
        game_dto,
        question_dto,
        answer_dto,
    ):
        """
        GIVEN: a restricted match with two question that can be
                played unlimited times
        WHEN: the user plays two times
        THEN: the system should behave correctly, each time
        """
        match = match_dto.new(is_restricted=True, times=1, notify_correct=True)
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question_1 = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
            time=None,
        )
        question_dto.save(question_1)
        answer_1 = answer_dto.new(question=question_1, text="UK", position=0, level=2)
        answer_dto.save(answer_1)
        user = user_dto.fetch(signed=True)
        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
                "password": match.password,
            },
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
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["question"] is None
        assert "match_uid" not in response.json()
        assert response.json()["was_correct"]
        assert response.json()["score"] > 0

    def test_8(
        self,
        client: TestClient,
        mocker,
        match_dto,
        game_dto,
        question_dto,
        answer_dto,
        user_dto,
    ):
        """
        GIVEN: a match that is valid at start time
        WHEN: the match expires before the user answers
        THEN: a response.BAD_REQUEST should be returned
        """
        mocker.patch(
            "app.domain_entities.match.Match.is_active",
            new_callable=mocker.PropertyMock,
            side_effect=[True, True, False],
        )
        match = match_dto.new(to_time=datetime.now())
        match_dto.save(match)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)
        answer = answer_dto.new(question=question, text="UK", position=1)
        answer_dto.save(answer)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
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
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_9(
        self,
        client: TestClient,
        db_session,
        match_dto,
        game_dto,
        question_dto,
        user_dto,
        answer_dto,
    ):
        """
        GIVEN: a treasure-hunt match, which is only
        WHEN: the user answers wrongly
        THEN: the response should contain the expected payload
        """
        match = match_dto.save(match_dto.new(treasure_hunt=True))
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        first_question = question_dto.new(
            text="Where is Graz?", game_uid=game.uid, position=0
        )
        question_dto.save(first_question)
        correct = answer_dto.new(
            question_uid=first_question.uid, text="Austria", position=1, level=2
        )
        answer_dto.save(correct)
        wrong = answer_dto.new(
            question_uid=first_question.uid, text="Germany", position=2, level=2
        )
        answer_dto.save(wrong)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)

        response = client.post(
            f"{settings.API_V1_STR}/play/start",
            json={
                "match_uid": match.uid,
                "user_uid": user.uid,
            },
        )
        assert response.ok
        attempt_uid = response.json()["attempt_uid"]

        response = client.post(
            f"{settings.API_V1_STR}/play/next",
            json={
                "match_uid": match.uid,
                "question_uid": first_question.uid,
                "answer_uid": wrong.uid,
                "user_uid": user.uid,
                "attempt_uid": attempt_uid,
            },
        )
        assert response.ok
        assert response.json() == {"question": None, "score": 0.0, "was_correct": None}
