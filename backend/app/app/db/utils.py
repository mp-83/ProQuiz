from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session, declarative_mixin

from app.db.session import get_db


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
    # TODO: to fix/update using db.event
    update_timestamp = Column(DateTime(timezone=True), nullable=True, onupdate=t_now)

    @declared_attr
    def __tablename__(self):
        return self.__name__.lower()

    def save_to(self, value, session: Session = Depends(get_db)):
        pass


class classproperty(property):
    def __get__(self, obj, objtype=None):
        return super(classproperty, self).__get__(objtype)

    def __set__(self, obj, value):
        super(classproperty, self).__set__(type(obj), value)

    def __delete__(self, obj):
        super(classproperty, self).__delete__(type(obj))
