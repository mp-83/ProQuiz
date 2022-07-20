from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.schemas.logical_validation import RetrieveObject
from app.exceptions import ValidateError


class ValidateEditMatch:
    def __init__(self, match_uid, match_in: dict, db_session: Session):
        self.match_uid = match_uid
        self.match_in = match_in
        self._session = db_session

    def valid_match(self):
        match = RetrieveObject(
            self.match_uid, otype="match", db_session=self._session
        ).get()
        if not match.is_started:
            return match

        raise ValidateError("Match started. Cannot be edited")

    def valid_questions(self):
        questions = self.match_in.get("questions") or []
        for question in questions:
            if "uid" in question:
                RetrieveObject(
                    question["uid"], otype="question", db_session=self._session
                ).get()
            if "game_uid" in question:
                RetrieveObject(
                    question["game_uid"], otype="game", db_session=self._session
                ).get()

    def is_valid(self):
        self.valid_questions()
        return self.valid_match()


class ValidateNewMatch:
    def __init__(self, match_in: dict, db_session: Session):
        self.from_time = match_in.get("from_time")
        self.to_time = match_in.get("to_time")
        self.name = match_in.get("name")
        self._session = db_session

    def valid_match(self):
        match = MatchDTO(session=self._session).get(name=self.name)
        if match:
            raise ValidateError("A Match with the same name already exists.")

    def validate_datetime(self):
        now = datetime.now(tz=timezone.utc)
        if self.from_time and self.from_time < now:
            raise ValidateError("from-time must be greater than now")

        if self.to_time and self.to_time < self.from_time:
            raise ValidateError("to-time must be greater than from-time")

    def is_valid(self):
        self.valid_match()
        self.validate_datetime()


class ValidateMatchImport:
    def __init__(self, match_uid, db_session: Session, game_uid=None):
        self.match_uid = match_uid
        self._session = db_session
        self.game_uid = game_uid

    def valid_match(self):
        return RetrieveObject(
            self.match_uid, otype="match", db_session=self._session
        ).get()

    def valid_game(self):
        return RetrieveObject(
            self.game_uid, otype="game", db_session=self._session
        ).get()

    def is_valid(self):
        if self.game_uid:
            self.valid_game()
        return self.valid_match()
