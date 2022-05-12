from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import Session, relationship

from app.db.base import Base
from app.db.utils import TableMixin


class Ranking(TableMixin, Base):
    __tablename__ = "rankings"

    user_uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", backref="user_rankings")

    match_uid = Column(Integer, ForeignKey("matches.uid"))
    match = relationship("Match", backref="rankings")

    score = Column(Integer, nullable=False)

    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    @property
    def session(self):
        return self._session

    def save(self):
        self.session.add(self)
        self.session.commit()
        return self

    @property
    def json(self):
        return {
            "match": {
                "name": self.match.name,
                "uid": self.match.uid,
            },
            "user": {"name": self.user.name},
        }


class Rankings:
    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def of_match(self, match_uid):
        return self._session.query(Ranking).filter_by(match_uid=match_uid).all()

    def all(self):
        return self._session.query(Ranking).all()
