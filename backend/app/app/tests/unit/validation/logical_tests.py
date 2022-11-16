from datetime import datetime, timedelta, timezone

import pytest

from app.domain_service.data_transfer.user import WordDigest
from app.domain_service.schemas.logical_validation import (
    RetrieveObject,
    ValidateEditMatch,
    ValidateMatchImport,
    ValidateNewMatch,
    ValidateNewQuestion,
    ValidatePlayCode,
    ValidatePlayLand,
    ValidatePlayNext,
    ValidatePlaySign,
    ValidatePlayStart,
)
from app.exceptions import NotFoundObjectError, ValidateError


class TestCaseRetrieveObject:
    def test_1(self, db_session):
        with pytest.raises(NotFoundObjectError):
            RetrieveObject(uid=1, otype="match", db_session=db_session).get()

    def test_2(self, db_session, user_dto):
        user = user_dto.fetch()
        obj = RetrieveObject(uid=user.uid, otype="user", db_session=db_session).get()
        assert obj == user


class TestCaseLandEndPoint:
    def test_1(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayLand(
                match_uhash="wrong-hash", db_session=db_session
            ).valid_match()


class TestCaseCodeEndPoint:
    def test_1(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayCode(match_code="2222", db_session=db_session).valid_match()

    def test_2(self, db_session, match_dto):
        """verifies match activeness"""
        ten_hours_ago = datetime.now() - timedelta(hours=40)
        two_hours_ago = datetime.now() - timedelta(hours=3600)
        match = match_dto.save(
            match_dto.new(
                with_code=True,
                from_time=ten_hours_ago,
                to_time=two_hours_ago,
            )
        )
        with pytest.raises(ValidateError) as err:
            ValidatePlayCode(match_code=match.code, db_session=db_session).valid_match()

        assert err.value.message == "Expired match"


class TestCaseSignEndPoint:
    def test_1(self, db_session, user_dto):
        original_email = "user@test.io"
        email_digest = WordDigest(original_email).value()
        token_digest = WordDigest("01112021").value()
        email = f"{email_digest}@progame.io"
        user_dto.save(
            user_dto.new(
                email=email,
                email_digest=email_digest,
                token_digest=token_digest,
            )
        )
        with pytest.raises(NotFoundObjectError) as err:
            ValidatePlaySign(
                original_email, "25121980", db_session=db_session
            ).is_valid()

        assert err.value.message == "Invalid email-token"


class TestCaseStartEndPoint:
    def test_1(self, db_session, match_dto, user_dto):
        """
        GIVEN: a restricted match
        WHEN: a public user who tries to start the match
        THEN: a ValidationError should be returned because
                public users can't access restricted matches
        """
        match = match_dto.new(is_restricted=True)
        match_dto.save(match)
        user = user_dto.new(email="user@test.project")
        user_dto.save(user)
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid,
                user_uid=user.uid,
                password=match.password,
                db_session=db_session,
            ).is_valid()

        assert err.value.message == "User cannot access this match"

    def test_2(self, db_session, match_dto, user_dto):
        """
        GIVEN: a restricted match
        WHEN: a public user who tries to start the match
        THEN: a ValidationError should be raise because password is empty
        """
        match = match_dto.new(is_restricted=True)
        match_dto.save(match)
        user = user_dto.fetch(signed=True)
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid,
                user_uid=user.uid,
                password="",
                db_session=db_session,
            ).is_valid()

        assert err.value.message == "Password is required for private matches"

    def test_3(self, db_session):
        """User does not exists"""
        with pytest.raises(NotFoundObjectError):
            ValidatePlayStart(user_uid=1, db_session=db_session).valid_user()

    def test_4(self, db_session, match_dto, user_dto):
        match = match_dto.new(is_restricted=True)
        match_dto.save(match)
        user_dto.fetch(signed=True)
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid, password="Invalid", db_session=db_session
            ).is_valid()

        assert err.value.message == "Password mismatch"


class TestCaseNextEndPoint:
    def test_1(
        self,
        db_session,
        match_dto,
        user_dto,
        game_dto,
        question_dto,
        answer_dto,
        reaction_dto,
    ):
        """
        GIVEN: a user that already answered to one question
        WHEN: he tries to answer it again
        THEN: a validation-error should be returned because they cannot
                exist two reactions with the same attempt-uid and answer
                (there is also a DB constraint that prevents two concurrent
                requests to reach at the same time)
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?", game_uid=game.uid, position=0
        )
        question_dto.save(question)
        answer = answer_dto.new(question=question, text="UK", position=1)
        answer_dto.save(answer)
        user = user_dto.fetch(email="user@test.project")

        reaction = reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
            answer_uid=answer.uid,
        )
        reaction_dto.save(reaction)

        with pytest.raises(ValidateError) as err:
            ValidatePlayNext(
                db_session=db_session, attempt_uid=reaction.attempt_uid
            ).valid_reaction(user=user, question=question)

        assert err.value.message == "Duplicate Reactions"

    def test_2(
        self,
        db_session,
        match_dto,
        user_dto,
        game_dto,
        question_dto,
        answer_dto,
        reaction_dto,
    ):
        """the attempt uid does not match any existing reaction of the user"""
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is London?", game_uid=game.uid, position=0
        )
        question_dto.save(question)
        user = user_dto.fetch(email="user@test.project")

        with pytest.raises(ValidateError) as err:
            ValidatePlayNext(
                db_session=db_session, attempt_uid="8e491fd30c4f4f37a8a1944a11d1f96a"
            ).valid_reaction(user=user, question=question)

        assert err.value.message == "Invalid attempt-uid"

    def test_3(self, db_session, question_dto, answer_dto):
        """
        GIVEN: a match with one question
        WHEN: the payload contains a the uid of another question
        THEN: an error is raised because the answer does not
                belong to the question
        """
        question = question_dto.new(text="Where is London?", position=0)
        other_question = question_dto.new(text="Where is Prague?", position=0)
        question_dto.save(question)
        answer = answer_dto.new(question_uid=question.uid, text="UK", position=1)
        answer_dto.save(answer)
        with pytest.raises(ValidateError) as err:
            ValidatePlayNext(answer_uid=answer.uid, db_session=db_session).valid_answer(
                other_question
            )
        assert err.value.message == "Invalid answer"

    def test_4(self, db_session, question_dto):
        """the question is provided only to fill the argument"""
        question = question_dto.new(text="Where is London?", position=0)
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(answer_uid=10000, db_session=db_session).valid_answer(
                question
            )

    def test_5(self, db_session):
        """User does not exists"""
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(user_uid=1, db_session=db_session).valid_user()

    def test_6(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(match_uid=1, db_session=db_session).valid_match()

    def test_7(self, db_session, match_dto, game_dto, question_dto, answer_dto):
        """
        GIVEN: a question already associated to `fixed` Answers
        WHEN: an open answer is sent
        THEN: an error should be raised
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0
        )
        question_dto.save(question)
        answer = answer_dto.new(question_uid=question.uid, text="UK", position=1)
        answer_dto.save(answer)
        with pytest.raises(ValidateError):
            ValidatePlayNext(
                answer_text="Paris is in France",
                db_session=db_session,
            ).valid_open_answer(question)

    def test_8(self, db_session, match_dto, game_dto, question_dto, open_answer_dto):
        """
        GIVEN: an open question
        WHEN: the user sends a blank answer_text
        THEN: validation succeeds. Although empty a new question
                is created for data consistency
        """
        match = match_dto.save(match_dto.new())
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)
        question = question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0
        )
        question_dto.save(question)
        count_before = open_answer_dto.count()
        ValidatePlayNext(answer_text="", db_session=db_session).valid_open_answer(
            question
        )
        assert open_answer_dto.count() == count_before + 1

    def test_9(self, db_session, match_dto, game_dto, question_dto, open_answer_dto):
        """
        GIVEN: a match without question
        WHEN: question used does not belong to the match
        THEN: validation fails

        to simplify the implementation of the test, and empty match
        is used and, as question, a template question (not associated
        to any game)
        """
        match = match_dto.save(match_dto.new())
        question = question_dto.new(text="Where is Paris?", position=0)
        question_dto.save(question)
        with pytest.raises(ValidateError) as err:
            ValidatePlayNext(
                match_uid=match.uid,
                question_uid=question.uid,
                db_session=db_session,
            ).valid_question(match)
        assert err.value.message == "Invalid question"


class TestCaseCreateMatch:
    def test_1(self, db_session):
        # to avoid from_time to be < datetime.now() when
        # the check is performed, the value is increased
        # by two seconds (or we mock datetime.now)
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(ValidateError) as e:
            ValidateNewMatch(
                {
                    "from_time": (now + timedelta(seconds=60)),
                    "to_time": (now - timedelta(minutes=10)),
                },
                db_session=db_session,
            ).is_valid()

        assert e.value.message == "to-time must be greater than from-time"

    def test_2(self, db_session):
        """from time value is in the past"""
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(ValidateError) as e:
            ValidateNewMatch(
                {
                    "from_time": (now - timedelta(seconds=1)),
                    "to_time": (now + timedelta(days=1)),
                },
                db_session=db_session,
            ).is_valid()

        assert e.value.message == "from-time must be greater than now"

    def test_3(self, db_session, match_dto):
        name = "New match"
        new_match = match_dto.new(name=name)
        match_dto.save(new_match)
        with pytest.raises(ValidateError) as e:
            ValidateNewMatch({"name": name}, db_session=db_session).is_valid()

        assert e.value.message == "A Match with the same name already exists."


class TestCaseMatchEdit:
    def test_1(
        self, db_session, match_dto, game_dto, question_dto, user_dto, reaction_dto
    ):
        """A match with at least one reaction can no longer be modified"""
        match_name = "New Match"
        match = match_dto.new(name=match_name)
        match_dto.save(match)

        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)

        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)
        user = user_dto.new(email="t@t.com")
        user_dto.save(user)

        reaction = reaction_dto.new(match=match, question=question, user=user)
        reaction_dto.save(reaction)

        with pytest.raises(ValidateError) as e:
            ValidateEditMatch(
                match_uid=match.uid, match_in={}, db_session=db_session
            ).is_valid()

        assert e.value.message == "Match started. Cannot be edited"

    def test_2(
        self, db_session, match_dto, game_dto, question_dto, user_dto, reaction_dto
    ):
        """the destination game does not exists"""
        match_name = "New Match"
        match = match_dto.new(name=match_name)
        match_dto.save(match)

        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)

        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)

        erroneous_uid = 30
        with pytest.raises(NotFoundObjectError) as e:
            ValidateEditMatch(
                match_uid=match.uid,
                match_in={
                    "questions": [{"uid": question.uid, "game_uid": erroneous_uid}]
                },
                db_session=db_session,
            ).is_valid()

        assert e.value.message == f"Game with Id:: {erroneous_uid} does not exist"


class TestCaseImportFromYaml:
    def test_1(self, db_session):
        """match does not exists"""
        with pytest.raises(NotFoundObjectError):
            ValidateMatchImport(match_uid=1, db_session=db_session).is_valid()

    def test_2(self, db_session, match_dto):
        """game does not exists"""
        erroneous_uid = 2
        match = match_dto.save(match_dto.new())
        with pytest.raises(NotFoundObjectError) as e:
            ValidateMatchImport(
                match_uid=match.uid, db_session=db_session, game_uid=erroneous_uid
            ).is_valid()

        assert e.value.message == f"Game with Id:: {erroneous_uid} does not exist"


class TestCaseQuestionCreate:
    def test_1(self):
        """when a question is created, either text or content_url
        can be provided
        """
        with pytest.raises(ValidateError):
            ValidateNewQuestion(question_in={"text": ""}).is_valid()

        with pytest.raises(ValidateError) as err:
            ValidateNewQuestion(
                question_in={"content_url": None, "text": ""}
            ).is_valid()

        assert err.value.message == "Either text or contentURL must be provided"
