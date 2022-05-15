from sqlalchemy import Column, String, select
from sqlalchemy.orm import Session

from app.constants import OPEN_ANSWER_TEXT_MAX_LENGTH, URL_LENGTH
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


class OpenAnswer(TableMixin, Base):
    __tablename__ = "open_answers"

    text = Column(String(OPEN_ANSWER_TEXT_MAX_LENGTH), nullable=False)
    content_url = Column(String(URL_LENGTH))
    # reactions: implicit backward relation

    @property
    def level(self):
        return

    def save(self):
        self._session.add(self)
        self._session.commit()
        return self


class OpenAnswers:
    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def count(self):
        return self._session.execute(select(OpenAnswer)).count()

    def all(self):
        return self._session.execute(select(OpenAnswer)).all()
