from app.constants import OPEN_ANSWER_TEXT_MAX_LENGTH, URL_LENGTH
from app.db.base import Base
from app.db.utils import StoreConfig, TableMixin, classproperty
from sqlalchemy import Column, String, select


class OpenAnswer(TableMixin, Base):
    __tablename__ = "open_answers"

    text = Column(String(OPEN_ANSWER_TEXT_MAX_LENGTH), nullable=False)
    content_url = Column(String(URL_LENGTH))
    # reactions: implicit backward relation

    @property
    def level(self):
        return

    @property
    def session(self):
        return StoreConfig().session

    def save(self):
        self.session.add(self)
        self.session.commit()
        return self


class OpenAnswers:
    @classproperty
    def session(self):
        return StoreConfig().session

    @classmethod
    def count(cls):
        return cls.session.execute(select(OpenAnswer)).count()

    @classmethod
    def all(cls):
        return cls.session.execute(select(OpenAnswer)).all()
