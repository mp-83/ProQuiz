from random import shuffle

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from app.constants import QUESTION_TEXT_MAX_LENGTH, URL_LENGTH
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import QAppenderClass, TableMixin


class Question(TableMixin, Base):
    __tablename__ = "questions"

    game_uid = Column(Integer, ForeignKey("games.uid", ondelete="SET NULL"))
    text = Column(String(QUESTION_TEXT_MAX_LENGTH), nullable=False)
    position = Column(Integer, nullable=False)
    time = Column(Integer)  # in seconds
    boolean = Column(Boolean, server_default="0")
    content_url = Column(String(URL_LENGTH))
    game = relationship("Game")
    reactions = relationship(
        "Reaction",
        viewonly=True,
        order_by="Reaction.uid",
        lazy="dynamic",
        query_class=QAppenderClass,
    )
    answers = relationship(
        "Answer",
        viewonly=True,
        order_by="Answer.uid",
        lazy="dynamic",
        query_class=QAppenderClass,
    )

    __table_args__ = (
        UniqueConstraint("game_uid", "position", name="ck_question_game_uid_position"),
    )

    def __init__(self, **kwargs):
        if not kwargs.get("text") and kwargs.get("content_url"):
            kwargs["text"] = "ContentURL"
        super().__init__(**kwargs)

    @property
    def is_open(self):
        return self.answers.count() == 0

    @property
    def answers_list(self):
        return [a.json for a in self.answers]

    @property
    def answers_to_display(self):
        _answers = [(a.uid, a.text or a.content_url) for a in self.answers.all()]
        shuffle(_answers)
        return _answers

    @property
    def is_template(self):
        return self.game_uid is None

    @property
    def answers_by_uid(self):
        return {a.uid: a for a in self.answers}

    @property
    def answers_by_position(self):
        return {a.position: a for a in self.answers}

    @property
    def json(self):
        return {
            "uid": self.uid,
            "text": self.text,
            "position": self.position,
            "boolean": self.boolean,
            "time": self.time,
            "answers": self.answers_list,
            "game": self.game,
        }
