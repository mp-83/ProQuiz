from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import QClass, TableMixin


class Game(TableMixin, Base):
    __tablename__ = "games"

    match_uid = Column(
        Integer, ForeignKey("matches.uid", ondelete="CASCADE"), nullable=False
    )
    match = relationship("Match", backref="games")
    questions = relationship(
        "Question",
        viewonly=True,
        order_by="Question.uid",
        lazy="dynamic",
        query_class=QClass,
    )
    index = Column(Integer, default=0)
    # when True question should be returned in order
    order = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("match_uid", "index", name="ck_game_match_uid_question"),
    )

    @property
    def first_question(self):
        return self.questions.filter_by(position=0).one_or_none()

    @property
    def json(self):
        return {"index": self.index}
