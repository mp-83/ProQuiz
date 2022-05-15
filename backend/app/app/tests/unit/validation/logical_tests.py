from datetime import datetime, timedelta

import pytest

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.reaction import ReactionDTO
from app.domain_service.data_transfer.user import UserDTO, WordDigest
from app.domain_service.validation.logical import (
    RetrieveObject,
    ValidateMatchImport,
    ValidateNewCodeMatch,
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
    def t_objectNotFound(self, db_session):
        with pytest.raises(NotFoundObjectError):
            RetrieveObject(uid=1, otype="match", db_session=db_session).get()

    def t_objectIsOfCorrectType(self, db_session):
        user = UserDTO(session=db_session).fetch()
        obj = RetrieveObject(uid=user.uid, otype="user", db_session=db_session).get()
        assert obj == user


class TestCaseLandEndPoint:
    def t_matchDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayLand(
                match_uhash="wrong-hash", db_session=db_session
            ).valid_match()


class TestCaseCodeEndPoint(TestCaseBase):
    def t_wrongCode(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayCode(match_code="2222", db_session=db_session).valid_match()

    def t_matchActiveness(self, db_session):
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
    def t_wrongToken(self, db_session):
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
    def t_publicUserRestrictedMatch(self, db_session):
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

    def t_privateMatchRequiresPassword(self, db_session):
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

    def t_userDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayStart(user_uid=1, db_session=db_session).valid_user()

    def t_invalidPassword(self, db_session):
        match = self.match_dto.new(is_restricted=True)
        self.match_dto.save(match)
        self.user_dto.fetch(signed=True)
        with pytest.raises(ValidateError) as err:
            ValidatePlayStart(
                match_uid=match.uid, password="Invalid", db_session=db_session
            ).is_valid()

        assert err.value.message == "Password mismatch"


class TestCaseNextEndPoint(TestCaseBase):
    def t_cannotAcceptSameReactionAgain(self, db_session):
        # despite the delay between the two (which respects the DB constraint)
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
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

    def t_answerDoesNotBelongToQuestion(self, db_session):
        # simulate a more realistic case
        match = self.match_dto.save(self.match_dto.new())
        game = self.game_dto.new(match_uid=match.uid, index=0)
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

    def t_answerDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(answer_uid=10000, db_session=db_session).valid_answer()

    def t_userDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(user_uid=1, db_session=db_session).valid_user()

    def t_matchDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidatePlayNext(match_uid=1, db_session=db_session).valid_match()


class TestCaseCreateMatch:
    def t_fromTimeGreaterThanToTime(self):
        # to avoid from_time to be < datetime.now() when
        # the check is performed, the value is increased
        # by two seconds (or we mock datetime.now)
        with pytest.raises(ValidateError) as e:
            ValidateNewCodeMatch(
                from_time=(datetime.now() + timedelta(seconds=2)),
                to_time=(datetime.now() - timedelta(seconds=10)),
            ).is_valid()

        assert e.value.message == "to-time must be greater than from-time"

    def t_fromTimeIsExpired(self):
        with pytest.raises(ValidateError) as e:
            ValidateNewCodeMatch(
                from_time=(datetime.now() - timedelta(seconds=1)),
                to_time=(datetime.now() + timedelta(days=1)),
            ).is_valid()

        assert e.value.message == "from-time must be greater than now"


class TestCaseImportFromYaml:
    def t_matchDoesNotExists(self, db_session):
        with pytest.raises(NotFoundObjectError):
            ValidateMatchImport(match_uid=1, db_session=db_session).valid_match()
