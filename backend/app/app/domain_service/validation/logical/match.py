from datetime import datetime

from sqlalchemy.orm import Session

from app.domain_service.validation.logical import RetrieveObject
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


class ValidateNewCodeMatch:
    def __init__(self, from_time, to_time):
        self.from_time = from_time
        self.to_time = to_time

    def is_valid(self):
        now = datetime.now()
        if self.from_time < now:
            raise ValidateError("from-time must be greater than now")

        if self.to_time < self.from_time:
            raise ValidateError("to-time must be greater than from-time")


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
