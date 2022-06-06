from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.schemas.logical import RetrieveObject
from app.exceptions import ValidateError


class ValidateEditMatch:
    def __init__(self, match_uid, db_session: Session):
        self.match_uid = match_uid
        self._session = db_session

    def valid_match(self):
        match = RetrieveObject(
            self.match_uid, otype="match", db_session=self._session
        ).get()
        if not match.is_started:
            return match

        raise ValidateError("Match started. Cannot be edited")

    def is_valid(self):
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
    def __init__(self, match_uid, db_session: Session):
        self.match_uid = match_uid
        self._session = db_session

    def valid_match(self):
        return RetrieveObject(
            self.match_uid, otype="match", db_session=self._session
        ).get()

    def is_valid(self):
        return self.valid_match()
