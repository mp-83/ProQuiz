from app.db.base import Base
from app.db.utils import StoreConfig, TableMixin
from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint


class Game(TableMixin, Base):
    __tablename__ = "games"

    match_uid = Column(
        Integer, ForeignKey("matches.uid", ondelete="CASCADE"), nullable=False
    )
    match = relationship("Match", backref="games")
    index = Column(Integer, default=0)
    # when True question should be returned in order
    order = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("match_uid", "index", name="ck_game_match_uid_question"),
    )

    @property
    def session(self):
        return StoreConfig().session

    def save(self):
        self.session.add(self)
        self.session.commit()
        return self

    def first_question(self):
        for q in self.questions:
            if q.position == 0:
                return q

    @property
    def ordered_questions(self):
        questions = {q.position: q for q in self.questions}
        _sorted = sorted(questions)
        return [questions[i] for i in _sorted]

    @property
    def json(self):
        return {"index": self.index}
