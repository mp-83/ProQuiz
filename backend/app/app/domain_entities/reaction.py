from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


class Reaction(TableMixin, Base):
    __tablename__ = "reactions"

    match_uid = Column(
        Integer, ForeignKey("matches.uid", ondelete="CASCADE"), nullable=False
    )
    match = relationship("Match", backref="reactions")
    question_uid = Column(
        Integer, ForeignKey("questions.uid", ondelete="CASCADE"), nullable=False
    )
    question = relationship("Question", backref="reactions")
    answer_uid = Column(
        Integer, ForeignKey("answers.uid", ondelete="SET NULL"), nullable=True
    )
    _answer = relationship("Answer", backref="reactions")
    open_answer_uid = Column(
        Integer, ForeignKey("open_answers.uid", ondelete="SET NULL"), nullable=True
    )
    _open_answer = relationship("OpenAnswer", backref="reactions")
    user_uid = Column(
        Integer, ForeignKey("users.uid", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", backref="reactions")
    game_uid = Column(
        Integer, ForeignKey("games.uid", ondelete="CASCADE"), nullable=False
    )
    game = relationship("Game", backref="reactions")

    # used to mark reactions of a user when drops out of a match
    dirty = Column(Boolean, default=False)
    answer_time = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float)

    __table_args__ = (
        UniqueConstraint(
            "question_uid", "answer_uid", "user_uid", "match_uid", "create_timestamp"
        ),
    )

    @property
    def answer(self):
        return self._open_answer if self.question.is_open else self._answer
