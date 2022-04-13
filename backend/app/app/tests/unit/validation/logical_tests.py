from datetime import datetime, timedelta

import pytest
from app.entities import (
    Answer,
    Game,
    Match,
    Question,
    Questions,
    Reaction,
    User,
)
from app.entities.user import UserFactory, WordDigest
from app.exceptions import NotFoundObjectError, ValidateError
from app.validation.logical import (
    RetrieveObject,
    ValidateMatchImport,
    ValidateNewCodeMatch,
    ValidatePlayCode,
    ValidatePlayLand,
    ValidatePlayNext,
    ValidatePlaySign,
    ValidatePlayStart,
)


class TestCaseRetrieveObject:
    def t_objectNotFound(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            RetrieveObject(uid=1, otype="match").get()

    def t_objectIsOfCorrectType(self, dbsession):
        user = UserFactory().fetch()
        obj = RetrieveObject(uid=user.uid, otype="user").get()
        assert obj == user


class TestCaseLandEndPoint:
    def t_matchDoesNotExists(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayLand(match_uhash="wrong-hash").valid_match()


class TestCaseCodeEndPoint:
    def t_wrongCode(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayCode(match_code="2222").valid_match()

    def t_matchActiveness(self, dbsession):
        ten_hours_ago = datetime.now() - timedelta(hours=40)
        two_hours_ago = datetime.now() - timedelta(hours=3600)
        match = Match(
            with_code=True, from_time=ten_hours_ago, to_time=two_hours_ago
        ).save()
        with pytest.raises(ValidateError) as err:
            ValidatePlayCode(match_code=match.code).valid_match()

        assert err.value.message == "Expired match"


class TestCaseSignEndPoint:
    def t_wrongToken(self, dbsession):
        original_email = "user@test.io"

        email_digest = WordDigest(original_email).value()
        token_digest = WordDigest("01112021").value()
        email = f"{email_digest}@progame.io"
        User(email=email, email_digest=email_digest, token_digest=token_digest).save()
        with pytest.raises(NotFoundObjectError):
            ValidatePlaySign(original_email, "25121980").is_valid()


class TestCaseStartEndPoint:
    def t_publicUserRestrictedMatch(self, dbsession):
        match = Match(is_restricted=True).save()
        user = User(email="user@test.project").save()
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid, user_uid=user.uid, password=match.password
            ).is_valid()

        assert err.value.message == "User cannot access this match"

    def t_privateMatchRequiresPassword(self, dbsession):
        match = Match(is_restricted=True).save()
        user = UserFactory(signed=True).fetch()
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid, user_uid=user.uid, password=""
            ).is_valid()

        assert err.value.message == "Password is required for private matches"

    def t_userDoesNotExists(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayStart(user_uid=1).valid_user()

    def t_invalidPassword(self, dbsession):
        match = Match(is_restricted=True).save()
        UserFactory(signed=True).fetch()
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(match_uid=match.uid, password="Invalid").is_valid()

        assert err.value.message == "Password mismatch"


class TestCaseNextEndPoint:
    def t_cannotAcceptSameReactionAgain(self, dbsession):
        # despite the delay between the two (which respects the DB constraint)
        match = Match().save()
        game = Game(match_uid=match.uid, index=0).save()
        question = Question(
            text="Where is London?", game_uid=game.uid, position=0
        ).save()
        answer = Answer(question=question, text="UK", position=1).save()
        user = UserFactory(email="user@test.project").fetch()

        Reaction(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
            answer_uid=answer.uid,
        ).save()

        with pytest.raises(ValidateError):
            ValidatePlayNext(
                user_uid=user.uid, question_uid=question.uid
            ).valid_reaction()

    def t_answerDoesNotBelongToQuestion(self, fillTestingDB, dbsession):
        # simulate a more realistic case
        question = Questions.get(uid=1)
        answer = Answer(question_uid=question.uid, text="UK", position=1).save()
        with pytest.raises(ValidateError):
            ValidatePlayNext(answer_uid=answer.uid, question_uid=10).valid_answer()

    def t_answerDoesNotExists(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(answer_uid=10000).valid_answer()

    def t_userDoesNotExists(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(user_uid=1).valid_user()

    def t_matchDoesNotExists(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(match_uid=1).valid_match()


class TestCaseCreateMatch:
    def t_fromTimeGreaterThanToTime(self, dbsession):
        # to avoid from_time to be < datetime.now() when
        # the check is performed, the value is increased
        # by two seconds (or we mock datetime.now)
        with pytest.raises(ValidateError) as e:
            ValidateNewCodeMatch(
                from_time=(datetime.now() + timedelta(seconds=2)),
                to_time=(datetime.now() - timedelta(seconds=10)),
            ).is_valid()

        assert e.value.message == "to-time must be greater than from-time"

    def t_fromTimeIsExpired(self, dbsession):
        with pytest.raises(ValidateError) as e:
            ValidateNewCodeMatch(
                from_time=(datetime.now() - timedelta(seconds=1)),
                to_time=(datetime.now() + timedelta(days=1)),
            ).is_valid()

        assert e.value.message == "from-time must be greater than now"


class TestCaseImportFromYaml:
    def t_matchDoesNotExists(self, dbsession):
        with pytest.raises(NotFoundObjectError):
            ValidateMatchImport(match_uid=1).valid_match()
