from sqlalchemy.orm import Session

from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.open_answer import OpenAnswerDTO
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

        # TODO: move this logic inside the method and pass the argument as below
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
        self.answer_text = kwargs.get("answer_text")
        self.attempt_uid = kwargs.get("attempt_uid")
        self._data = {}
        self.user_dto = UserDTO(session=db_session)

    def valid_reaction(self, question, user):
        attempt_reactions = user.reactions.filter_by(attempt_uid=self.attempt_uid)
        if attempt_reactions.count() == 0:
            raise ValidateError("Invalid attempt-uid")

        reaction = user.reactions.filter_by(
            question_uid=question.uid, attempt_uid=self.attempt_uid
        ).one_or_none()
        if not reaction:
            raise ValidateError("Invalid reaction")

        if reaction.answer:  # TODO and not question.is_open:
            raise ValidateError("Duplicate Reactions")
        return reaction

    def valid_answer(self, question):
        if self.answer_uid is None:
            return

        answer = RetrieveObject(
            self.answer_uid, otype="answer", db_session=self._session
        ).get()

        if answer in question.answers:
            return answer

        raise ValidateError("Invalid answer")

    def valid_open_answer(self, question):
        if self.answer_text is None:
            return

        if question.is_open:
            open_answer_dto = OpenAnswerDTO(session=self._session)
            open_answer = open_answer_dto.new(text=self.answer_text)
            open_answer_dto.save(open_answer)
            return open_answer

        raise ValidateError("Invalid answer")

    def valid_user(self):
        return RetrieveObject(
            self.user_uid, otype="user", db_session=self._session
        ).get()

    def valid_match(self):
        match = RetrieveObject(
            self.match_uid, otype="match", db_session=self._session
        ).get()
        if not match.is_active:
            raise ValidateError("Expired match")

        return match

    def valid_question(self, match):
        question = RetrieveObject(
            self.question_uid, otype="question", db_session=self._session
        ).get()

        if question in match.questions_list:
            return question
        raise ValidateError("Invalid question")

    def is_valid(self):
        # expected to run in sequence
        match = self.valid_match()
        self._data["match"] = match
        question = self.valid_question(match)
        self._data["question"] = question
        answer = self.valid_answer(question)
        self._data["answer"] = answer
        open_answer = self.valid_open_answer(question)
        self._data["open_answer"] = open_answer
        user = self.valid_user()
        self._data["user"] = user
        reaction = self.valid_reaction(user=user, question=question)
        self._data["attempt_uid"] = reaction.attempt_uid
        return self._data
