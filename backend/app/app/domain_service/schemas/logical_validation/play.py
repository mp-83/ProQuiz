from sqlalchemy.orm import Session

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.user import UserDTO, WordDigest
from app.domain_service.schemas.logical_validation import RetrieveObject
from app.exceptions import NotFoundObjectError, ValidateError


class ValidatePlayLand:
    def __init__(self, match_uhash: str, db_session: Session):
        self.match_uhash = match_uhash
        self._session = db_session

    def valid_match(self):
        match = MatchDTO(session=self._session).get(uhash=self.match_uhash)
        if not match:
            raise NotFoundObjectError()

        if match.is_active:
            return match

        raise ValidateError("Expired match")

    def is_valid(self):
        return {"match": self.valid_match()}


class ValidatePlayCode:
    def __init__(self, match_code: str, db_session: Session):
        self.match_code = match_code
        self._session = db_session

    def valid_match(self):
        match = MatchDTO(session=self._session).get(code=self.match_code)
        if not match:
            raise NotFoundObjectError()

        if match.is_active:
            return match

        raise ValidateError("Expired match")

    def is_valid(self):
        return {"match": self.valid_match()}


class ValidatePlaySign:
    def __init__(self, email: str, token: str, db_session: Session):
        self.original_email = email
        self.token = token
        self._session = db_session

    def valid_user(self):
        email_digest = WordDigest(self.original_email).value()
        token_digest = WordDigest(self.token).value()
        dto = UserDTO(session=self._session)
        user = dto.get(email_digest=email_digest, token_digest=token_digest)
        if user:
            return user
        raise NotFoundObjectError("Invalid email-token")

    def is_valid(self):
        return {"user": self.valid_user()}


class ValidatePlayStart:
    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        self.match_uid = kwargs.get("match_uid")
        self.user_uid = kwargs.get("user_uid")
        self.password = kwargs.get("password")

    def valid_user(self):
        dto = UserDTO(session=self._session)
        user = dto.get(uid=self.user_uid)
        if self.user_uid and not user:
            raise NotFoundObjectError()
        return user

    def valid_match(self):
        return RetrieveObject(
            self.match_uid, otype="match", db_session=self._session
        ).get()

    def is_valid(self):
        """Verifies match accessibility"""
        match = self.valid_match()
        user = self.valid_user()

        if not match.is_active:
            raise ValidateError("Expired match")

        if match.is_restricted:
            if not self.password:
                raise ValidateError("Password is required for private matches")

            if self.password != match.password:
                raise ValidateError("Password mismatch")

        if user and user.signed != match.is_restricted:
            raise ValidateError("User cannot access this match")

        data = {"match": match}
        if user:
            data.update(user=user)
        return data


class ValidatePlayNext:
    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        self.match_uid = kwargs.get("match_uid")
        self.answer_uid = kwargs.get("answer_uid")
        self.user_uid = kwargs.get("user_uid")
        self.question_uid = kwargs.get("question_uid")
        self._data = {}
        self.user_dto = UserDTO(session=db_session)

    def valid_reaction(self):
        user = self._data.get("user")
        if not user:
            user = self.user_dto.get(uid=self.user_uid)

        question = self._data.get("question")
        if not question:
            question = QuestionDTO(session=self._session).get(uid=self.question_uid)
            self._data["question"] = question

        reaction = user.reactions.filter_by(question_uid=question.uid).one_or_none()
        if reaction and reaction.answer:
            raise ValidateError("Duplicate Reactions")

    def valid_answer(self):
        if self.answer_uid is None:
            return

        answer = AnswerDTO(session=self._session).get(uid=self.answer_uid)
        if answer is None:
            raise NotFoundObjectError("Unexisting answer")

        question = QuestionDTO(session=self._session).get(uid=self.question_uid)
        if question and answer in question.answers:
            self._data["answer"] = answer
            return

        raise ValidateError("Invalid answer")

    def valid_user(self):
        user = self.user_dto.get(uid=self.user_uid)
        if user:
            self._data["user"] = user
            return

        raise NotFoundObjectError()

    def valid_match(self):
        match = RetrieveObject(
            self.match_uid, otype="match", db_session=self._session
        ).get()
        self._data["match"] = match

    def is_valid(self):
        # expected to run in sequence
        self.valid_answer()
        self.valid_user()
        self.valid_match()
        self.valid_reaction()
        return self._data
