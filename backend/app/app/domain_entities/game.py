from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import Session, relationship
from sqlalchemy.schema import UniqueConstraint

from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


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

    def __init__(self, db_session: Session = None, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def save(self):
        self._session.add(self)
        self._session.commit()
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
