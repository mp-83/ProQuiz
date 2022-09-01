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


class QAppenderClass(Query):
    """"""

    separator = "__"
    str_operator_map = {
        "gt": "__gt__",
        "in": "in_",
        "notin": "notin_",
        "lt": "__lt__",
    }

    def __init__(self, *args, **kwargs):
        self.data = None
        super(QAppenderClass, self).__init__(*args, **kwargs)

    def all(self):
        if not self.data:
            self.data = super().all()
        return self.data

    def get_entity(self):
        return self._entity_from_pre_ent_zero().entity

    def _entity_descriptor(self, key):
        entity = self.get_entity()
        try:
            return getattr(entity, key)
        except AttributeError:
            return

    def join_clauses_with_op(self, **clauses):
        # if self.get_entity().__name__ == "Reaction":
        #     import pdb;pdb.set_trace()

        result = []
        for col_name, op_value_tuple in clauses.items():
            cmp_op, value = op_value_tuple
            col = self._entity_descriptor(col_name)
            result.append(getattr(col, cmp_op)(value))
        return result

    def split_clauses(self, **filters_kws):
        simple = {}
        with_op = {}
        for key, value in filters_kws.items():
            if self.separator in key:
                col_name, op = key.split(self.separator)
                op = self.str_operator_map.get(op)
                if not op:
                    continue
                with_op[col_name] = (op, value)
            else:
                simple[key] = value

        return simple, with_op

    def filter_by(self, **kwargs):
        simple, with_op = self.split_clauses(**kwargs)
        f_clause = super(QAppenderClass, self).filter_by(**simple)
        op_clause = self.join_clauses_with_op(**with_op)
        return f_clause.filter(*op_clause)

    def filter_join(self, position):
        # TEMPORARY METHOD
        from app.domain_entities.game import Game
        from app.domain_entities.question import Question

        return self.join(Question, Game).filter(
            Question.position == position, Game.index == 0
        )
