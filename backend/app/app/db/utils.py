from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.ext.declarative import declared_attr


def t_now():
    return datetime.now(tz=timezone.utc)


class StoreConfig:
    _instance = None
    _config = None
    _session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StoreConfig, cls).__new__(cls)
        return cls._instance

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, value):
        self._config = value

    @property
    def session(self):
        factory = self._config.registry.get("dbsession_factory")
        if self._session is None:
            self._session = factory()
        if not self._session.is_active:
            self._session = factory()

        return self._session


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


class classproperty(property):
    def __get__(self, obj, objtype=None):
        return super(classproperty, self).__get__(objtype)

    def __set__(self, obj, value):
        super(classproperty, self).__set__(type(obj), value)

    def __delete__(self, obj):
        super(classproperty, self).__delete__(type(obj))
