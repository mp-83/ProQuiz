from sqlalchemy import Boolean, Column, ForeignKey, Integer, text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import QAppenderClass, TableMixin


class Game(TableMixin, Base):
    __tablename__ = "games"

    match_uid = Column(
        Integer, ForeignKey("matches.uid", ondelete="CASCADE"), nullable=False
    )
    index = Column(Integer, server_default=text("0"))
    # when True question should be returned in order
    order = Column(Boolean, server_default="1")
    match = relationship("Match")
    questions = relationship(
        "Question",
        viewonly=True,
        order_by="Question.uid",
        lazy="dynamic",
        query_class=QAppenderClass,
    )
    reactions = relationship(
        "Reaction",
        viewonly=True,
        order_by="Reaction.uid",
        lazy="dynamic",
        query_class=QAppenderClass,
    )

    __table_args__ = (
        UniqueConstraint("match_uid", "index", name="ck_game_match_uid_question"),
    )

    @property
    def first_question(self):
        return self.questions.filter_by(position=0).one_or_none()

    @property
    def json(self):
        return {"index": self.index}
