from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query, declarative_mixin


def t_now():
    return datetime.now(tz=timezone.utc)


class StoreConfig:
    _instance = None
    _session = None
    _factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StoreConfig, cls).__new__(cls)
        return cls._instance

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, value):
        self._session = value


@declarative_mixin
class TableMixin:

    __mapper_args__ = {"always_refresh": True}

    uid = Column(Integer, primary_key=True)
    create_timestamp = Column(DateTime(timezone=True), nullable=False, default=t_now)
    update_timestamp = Column(DateTime(timezone=True), nullable=True, onupdate=t_now)

    @declared_attr
    def __tablename__(self):
        return self.__name__.lower()


class QClass(Query):
    """"""

    def __init__(self, *args, **kwargs):
        self.data = None
        super(QClass, self).__init__(*args, **kwargs)

    def all(self):
        if not self.data:
            self.data = super().all()
        return self.data

    def exclude(self, values):
        from app.domain_entities.question import Question

        return self.filter(Question.uid.notin_(values))
