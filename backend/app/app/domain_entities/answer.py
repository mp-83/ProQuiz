from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import CheckConstraint, UniqueConstraint

from app.constants import ANSWER_TEXT_MAX_LENGTH, URL_LENGTH
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


class Answer(TableMixin, Base):
    __tablename__ = "answers"

    question_uid = Column(
        Integer, ForeignKey("questions.uid", ondelete="CASCADE"), nullable=False
    )
    question = relationship("Question", backref="answers")
    # reactions: implicit backward relation

    position = Column(Integer, nullable=False)
    text = Column(String(ANSWER_TEXT_MAX_LENGTH))
    bool_value = Column(Boolean)
    # whether the content of the answer is an image or any external source
    content_url = Column(String(URL_LENGTH))
    # no constraint are defined as there might be more than one correct answer
    is_correct = Column(Boolean, default=False)
    level = Column(Integer)

    __table_args__ = (
        UniqueConstraint("question_uid", "text"),
        UniqueConstraint("question_uid", "bool_value"),
        CheckConstraint(
            "CASE WHEN text NOTNULL THEN bool_value IS NULL END",
            name="ck_answers_text_notnull",
        ),
        CheckConstraint(
            "CASE WHEN bool_value NOTNULL THEN text IS NULL END",
            name="ck_answers_bool_value_notnull",
        ),
    )

    @property
    def json(self):
        return {
            "uid": self.uid,
            "text": self.text,
            "question_uid": self.question_uid,
            "is_correct": self.is_correct,
            "position": self.position,
            "level": self.level,
            "content_url": self.content_url,
        }
