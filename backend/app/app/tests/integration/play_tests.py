from datetime import datetime, timedelta, timezone

from app.entities import Answer, Game, Match, Question, Rankings, User
from app.entities.user import UserFactory, WordDigest


class TestCaseBadRequest:
    def t_endpoints(self, testapp):
        # TODO to improve: if the enpoint url is malformed it the /play
        # enpoint matches (route matching logic).
        endpoints = ["/play/BAD", "/play/start", "/play/next", "/play/sign"]
        for endpoint in endpoints:
            testapp.post_json(
                endpoint,
                {"match_uid": None},
                headers={"X-CSRF-Token": testapp.get_csrf_token()},
                status=400,
            )


class TestCasePlayLand:
    # the test scenario for land/404 is already tested above
    def t_playLand(self, testapp):
        match = Match(with_code=False).save()
        response = testapp.post(
            f"/play/{match.uhash}",
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )
        assert response.json["match"] == match.uid


class TestCasePlayCode:
    def t_playCode(self, testapp):
        in_one_hour = datetime.now() + timedelta(hours=1)
        match = Match(with_code=True, expires=in_one_hour).save()
        response = testapp.post_json(
            "/play/code",
            {"match_code": match.code},
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )
        # the user.uid value can't be known ahead, but it will be > 0
        assert response.json["user"]
        assert response.json["match"] == match.uid


class TestCasePlaySign:
    def t_successfulSignReturnsExisting(self, testapp):
        Match(with_code=True).save()
        email_digest = WordDigest("user@test.io").value()
        token_digest = WordDigest("01112021").value()
        email = f"{email_digest}@progame.io"
        user = User(
            email=email, email_digest=email_digest, token_digest=token_digest
        ).save()
        response = testapp.post_json(
            "/play/sign",
            {"email": "user@test.io", "token": "01112021"},
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )
        assert response.json["user"] == user.uid


class TestCasePlayStart:
    def t_unexistentMatch(self, testapp):
        testapp.post_json(
            "/play/start",
            {"match_uid": 100, "user_uid": 1},
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=404,
        )

    def t_startExpiredMatch(self, testapp):
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        match = Match(expires=one_hour_ago).save()
        user = UserFactory(signed=match.is_restricted).fetch()
        testapp.post_json(
            "/play/start",
            {"match_uid": match.uid, "user_uid": user.uid},
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=400,
        )

    def t_startMatchAndUserIsImplicitlyCreated(self, testapp):
        match = Match(is_restricted=False).save()
        game = Game(match_uid=match.uid).save()
        question = Question(game_uid=game.uid, text="1+1 is = to", position=0).save()
        UserFactory(signed=match.is_restricted).fetch()

        response = testapp.post_json(
            "/play/start",
            {"match_uid": match.uid},
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )

        assert response.json["match"] == match.uid
        assert response.json["question"] == question.json
        assert response.json["question"]["answers"] == []
        # the user.uid value can't be known ahead, but it will be > 0
        assert response.json["user"]

    def t_startMatchWithoutQuestion(self, testapp):
        match = Match(is_restricted=False).save()
        game = Game(match_uid=match.uid).save()
        user = UserFactory(signed=match.is_restricted).fetch()

        response = testapp.post_json(
            "/play/start",
            {"match_uid": match.uid, "user_uid": user.uid},
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=400,
        )
        assert response.json["error"] == f"Game {game.uid} has no questions"

    # the password feature is tested more thoroughly in the logical tests
    def t_startRestrictedMatchUsingPassword(self, testapp):
        match = Match(is_restricted=True).save()
        game = Game(match_uid=match.uid).save()
        question = Question(game_uid=game.uid, text="1+1 is = to", position=0).save()
        user = UserFactory(signed=match.is_restricted).fetch()

        response = testapp.post_json(
            "/play/start",
            {"match_uid": match.uid, "user_uid": user.uid, "password": match.password},
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )

        assert response.json["question"] == question.json


class TestCasePlayNext:
    def t_duplicateSameReaction(self, testapp, trivia_match):
        match = trivia_match
        user = UserFactory(signed=match.is_restricted).fetch()
        question = match.questions[0][0]
        answer = question.answers_by_position[0]

        testapp.post_json(
            "/play/next",
            {
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )
        testapp.post_json(
            "/play/next",
            {
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=400,
        )

    def t_unexistentQuestion(self, testapp):
        testapp.post_json(
            "/play/next",
            {
                "match_uid": 1,
                "question_uid": 1,
                "answer_uid": 1,
                "user_uid": 1,
            },
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=404,
        )

    def t_answerQuestion(self, testapp, trivia_match):
        match = trivia_match
        user = UserFactory(signed=match.is_restricted).fetch()
        question = match.questions[0][0]
        answer = question.answers_by_position[0]

        response = testapp.post_json(
            "/play/next",
            {
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )
        assert response.json["question"] == match.questions[0][1].json
        assert response.json["user"] == user.uid

    def t_completeMatch(self, testapp):
        match = Match().save()
        first_game = Game(match_uid=match.uid, index=0).save()
        question = Question(
            text="Where is London?", game_uid=first_game.uid, position=0, time=2
        ).save()
        answer = Answer(question=question, text="UK", position=1, level=2).save()
        user = User(email="user@test.project").save()
        response = testapp.post_json(
            "/play/next",
            {
                "match_uid": match.uid,
                "question_uid": question.uid,
                "answer_uid": answer.uid,
                "user_uid": user.uid,
            },
            headers={"X-CSRF-Token": testapp.get_csrf_token()},
            status=200,
        )
        assert response.json["question"] is None
        assert len(Rankings.of_match(match.uid)) == 1
