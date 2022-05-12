from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import Session, relationship

from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


class Ranking(TableMixin, Base):
    __tablename__ = "rankings"

    user_uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", backref="user_rankings")

    match_uid = Column(Integer, ForeignKey("matches.uid"))
    match = relationship("Match", backref="rankings")

    score = Column(Integer, nullable=False)

    def __init__(self, db_session: Session = None, **kwargs):
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
