from datetime import datetime, timedelta, timezone

import pytest

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.domain_service.data_transfer.user import UserDTO, WordDigest
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


class TestCaseBase:
    @pytest.fixture(autouse=True)
    def setUp(self, db_session):
        self.question_dto = QuestionDTO(session=db_session)
        self.answer_dto = AnswerDTO(session=db_session)
        self.reaction_dto = ReactionDTO(session=db_session)
        self.match_dto = MatchDTO(session=db_session)
        self.game_dto = GameDTO(session=db_session)
        self.user_dto = UserDTO(session=db_session)


class TestCaseRetrieveObject:
    def test_objectNotFound(self, db_session):
        with pytest.raises(NotFoundObjectError):
            RetrieveObject(uid=1, otype="match", db_session=db_session).get()

    def test_objectIsOfCorrectType(self, db_session):
        user = UserDTO(session=db_session).fetch()
        obj = RetrieveObject(uid=user.uid, otype="user", db_session=db_session).get()
        assert obj == user


class TestCaseLandEndPoint:
    def test_matchDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayLand(
                match_uhash="wrong-hash", db_session=db_session
            ).valid_match()


class TestCaseCodeEndPoint(TestCaseBase):
    def test_wrongCode(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayCode(match_code="2222", db_session=db_session).valid_match()

    def test_matchActiveness(self, db_session):
        ten_hours_ago = datetime.now() - timedelta(hours=40)
        two_hours_ago = datetime.now() - timedelta(hours=3600)
        match = self.match_dto.save(
            self.match_dto.new(
                with_code=True,
                from_time=ten_hours_ago,
                to_time=two_hours_ago,
            )
        )
        with pytest.raises(ValidateError) as err:
            ValidatePlayCode(match_code=match.code, db_session=db_session).valid_match()

        assert err.value.message == "Expired match"


class TestCaseSignEndPoint:
    def test_wrongToken(self, db_session):
        original_email = "user@test.io"

        email_digest = WordDigest(original_email).value()
        token_digest = WordDigest("01112021").value()
        email = f"{email_digest}@progame.io"
        user_dto = UserDTO(session=db_session)
        user_dto.save(
            user_dto.new(
                email=email,
                email_digest=email_digest,
                token_digest=token_digest,
            )
        )
        with pytest.raises(NotFoundObjectError):
            ValidatePlaySign(
                original_email, "25121980", db_session=db_session
            ).is_valid()


class TestCaseStartEndPoint(TestCaseBase):
    def test_publicUserRestrictedMatch(self, db_session):
        match = self.match_dto.new(is_restricted=True)
        self.match_dto.save(match)
        user = self.user_dto.new(email="user@test.project")
        self.user_dto.save(user)
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid,
                user_uid=user.uid,
                password=match.password,
                db_session=db_session,
            ).is_valid()

        assert err.value.message == "User cannot access this match"

    def test_privateMatchRequiresPassword(self, db_session):
        match = self.match_dto.new(is_restricted=True)
        self.match_dto.save(match)
        user = self.user_dto.fetch(signed=True)
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid,
                user_uid=user.uid,
                password="",
                db_session=db_session,
            ).is_valid()

        assert err.value.message == "Password is required for private matches"

    def test_userDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayStart(user_uid=1, db_session=db_session).valid_user()

    def test_invalidPassword(self, db_session):
        match = self.match_dto.new(is_restricted=True)
        self.match_dto.save(match)
        self.user_dto.fetch(signed=True)
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid, password="Invalid", db_session=db_session
            ).is_valid()

        assert err.value.message == "Password mismatch"


class TestCaseNextEndPoint(TestCaseBase):
    def test_cannotAcceptSameReactionAgain(self, db_session):
        # despite the delay between the two (which respects the DB constraint)
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question)
        answer = self.answer_dto.new(question=question, text="UK", position=1)
        self.answer_dto.save(answer)
        user = self.user_dto.fetch(email="user@test.project")

        reaction = self.reaction_dto.new(
            match=match,
            question=question,
            user=user,
            game_uid=game.uid,
            answer_uid=answer.uid,
        )
        self.reaction_dto.save(reaction)

        with pytest.raises(ValidateError):
            ValidatePlayNext(
                user_uid=user.uid, question_uid=question.uid, db_session=db_session
            ).valid_reaction()

    def test_answerDoesNotBelongToQuestion(self, db_session):
        # simulate a more realistic case
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is London?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question)
        answer = self.answer_dto.new(question_uid=question.uid, text="UK", position=1)
        self.answer_dto.save(answer)
        with pytest.raises(ValidateError):
            ValidatePlayNext(
                answer_uid=answer.uid, question_uid=10, db_session=db_session
            ).valid_answer()

    def test_answerDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(answer_uid=10000, db_session=db_session).valid_answer()

    def test_userDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(user_uid=1, db_session=db_session).valid_user()

    def test_matchDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(match_uid=1, db_session=db_session).valid_match()

    def test_6(self, db_session):
        """
        GIVEN: a question already associated to `fixed` Answers
        WHEN: an open answer is sent
        THEN: an error should be raised
        """
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question)
        answer = self.answer_dto.new(question_uid=question.uid, text="UK", position=1)
        self.answer_dto.save(answer)
        with pytest.raises(ValidateError):
            ValidatePlayNext(
                answer_text="Paris is in France",
                question_uid=question.uid,
                db_session=db_session,
            ).valid_open_answer()

    def test_7(self, db_session, open_answer_dto):
        """
        GIVEN: an open question
        WHEN: the user sends a answer_text
        THEN: no error should be raised and the OpenAnswer be
                created inside the validation process
        """
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question)
        answer_text = "Paris is in France"
        ValidatePlayNext(
            answer_text=answer_text,
            question_uid=question.uid,
            db_session=db_session,
        ).valid_open_answer()
        assert open_answer_dto.get(text=answer_text)

    def test_8(self, db_session, open_answer_dto):
        """
        GIVEN: an open question
        WHEN: the user sends a blank answer_text
        THEN: validation succeeds. Although empty a new question
                is created for data consistency
        """
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question)
        count_before = open_answer_dto.count()
        ValidatePlayNext(
            answer_text="",
            question_uid=question.uid,
            db_session=db_session,
        ).valid_open_answer()
        assert open_answer_dto.count() == count_before + 1

    def test_9(self, db_session, open_answer_dto):
        """
        GIVEN: an open question
        WHEN: the user sends a blank answer_text
        THEN: validation succeeds. Although empty a new question
                is created for data consistency
        """
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid)
        self.game_dto.save(game)
        question = self.question_dto.new(
            text="Where is Paris?", game_uid=game.uid, position=0
        )
        self.question_dto.save(question)
        count_before = open_answer_dto.count()
        user = self.user_dto.fetch(email="user@test.project")

        with pytest.raises(ValidateError):
            ValidatePlayNext(
                answer_text="",
                question_uid=question.uid,
                db_session=db_session,
                attempt_uid="cfaf396f41f74c0688a09ba334d0fdeb",
                user_uid=user.uid,
                match_uid=match.uid,
            ).is_valid()
        assert open_answer_dto.count() == count_before + 1


class TestCaseCreateMatch:
    now = datetime.now(tz=timezone.utc)

    def test_fromTimeGreaterThanToTime(self, db_session):
        # to avoid from_time to be < datetime.now() when
        # the check is performed, the value is increased
        # by two seconds (or we mock datetime.now)
        with pytest.raises(ValidateError) as e:
            ValidateNewMatch(
                {
                    "from_time": (self.now + timedelta(seconds=60)),
                    "to_time": (self.now - timedelta(minutes=10)),
                },
                db_session=db_session,
            ).is_valid()

        assert e.value.message == "to-time must be greater than from-time"

    def test_fromTimeIsExpired(self, db_session):
        with pytest.raises(ValidateError) as e:
            ValidateNewMatch(
                {
                    "from_time": (self.now - timedelta(seconds=1)),
                    "to_time": (self.now + timedelta(days=1)),
                },
                db_session=db_session,
            ).is_valid()

        assert e.value.message == "from-time must be greater than now"

    def test_matchWithSameNameAlreadyExists(self, db_session):
        name = "New match"
        dto = MatchDTO(session=db_session)
        new_match = dto.new(name=name)
        dto.save(new_match)
        with pytest.raises(ValidateError) as e:
            ValidateNewMatch({"name": name}, db_session=db_session).is_valid()

        assert e.value.message == "A Match with the same name already exists."


class TestCaseMatchEdit:
    def test_matchCannotBeChangedIfStarted(self, db_session):
        match_name = "New Match"
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(name=match_name)
        match_dto.save(match)

        game_dto = GameDTO(session=db_session)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)

        question_dto = QuestionDTO(session=db_session)
        question = question_dto.new(
            text="Where is London?",
            game_uid=game.uid,
            position=0,
        )
        question_dto.save(question)
        user_dto = UserDTO(session=db_session)
        user = user_dto.new(email="t@t.com")
        user_dto.save(user)

        reaction_dto = ReactionDTO(session=db_session)
        reaction = reaction_dto.new(match=match, question=question, user=user)
        reaction_dto.save(reaction)

        with pytest.raises(ValidateError) as e:
            ValidateEditMatch(
                match_uid=match.uid, match_in={}, db_session=db_session
            ).is_valid()

        assert e.value.message == "Match started. Cannot be edited"

    def test_moveQuestionToNotExistingGame(self, db_session):
        match_name = "New Match"
        match_dto = MatchDTO(session=db_session)
        match = match_dto.new(name=match_name)
        match_dto.save(match)

        game_dto = GameDTO(session=db_session)
        game = game_dto.new(match_uid=match.uid)
        game_dto.save(game)

        question_dto = QuestionDTO(session=db_session)
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
    def test_matchDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidateMatchImport(match_uid=1, db_session=db_session).is_valid()

    def test_gameDoesNotExists(self, db_session):
        erroneous_uid = 2
        match_dto = MatchDTO(session=db_session)
        match = match_dto.save(match_dto.new())
        with pytest.raises(NotFoundObjectError) as e:
            ValidateMatchImport(
                match_uid=match.uid, db_session=db_session, game_uid=erroneous_uid
            ).is_valid()

        assert e.value.message == f"Game with Id:: {erroneous_uid} does not exist"


class TestCaseQuestionCreate:
    def test_eitherTextOrContentUrl(self):
        with pytest.raises(ValidateError):
            ValidateNewQuestion(question_in={"text": ""}).is_valid()

        with pytest.raises(ValidateError):
            ValidateNewQuestion(
                question_in={"content_url": None, "text": ""}
            ).is_valid()
