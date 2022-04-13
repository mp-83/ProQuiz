from app.db.base import Base
from app.db.utils import StoreConfig, TableMixin, classproperty
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship


class Ranking(TableMixin, Base):
    __tablename__ = "rankings"

    user_uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", backref="user_rankings")

    match_uid = Column(Integer, ForeignKey("matches.uid"))
    match = relationship("Match", backref="rankings")

    score = Column(Integer, nullable=False)

    @property
    def session(self):
        return StoreConfig().session

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
    @classproperty
    def session(self):
        return StoreConfig().session

    @classmethod
    def of_match(cls, match_uid):
        return cls.session.query(Ranking).filter_by(match_uid=match_uid).all()

    @classmethod
    def all(cls):
        return cls.session.query(Ranking).all()
