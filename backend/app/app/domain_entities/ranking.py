from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


class Ranking(TableMixin, Base):
    __tablename__ = "rankings"

    user_uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", backref="user_rankings")

    match_uid = Column(Integer, ForeignKey("matches.uid"))
    match = relationship("Match")

    score = Column(Integer, nullable=False)

    @property
    def json(self):
        return {
            "match": {
                "name": self.match.name,
                "uid": self.match.uid,
            },
            "user": {"name": self.user.name},
        }
