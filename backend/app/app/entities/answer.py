from app.constants import ANSWER_TEXT_MAX_LENGTH, URL_LENGTH
from app.db.base import Base
from app.db.utils import StoreConfig, TableMixin, classproperty
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, select
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint


class Answer(TableMixin, Base):
    __tablename__ = "answers"

    question_uid = Column(
        Integer, ForeignKey("questions.uid", ondelete="CASCADE"), nullable=False
    )
    question = relationship("Question", backref="answers")
    # reactions: implicit backward relation

    position = Column(Integer, nullable=False)
    text = Column(String(ANSWER_TEXT_MAX_LENGTH), nullable=False)
    # whether the content of the answer is an image or any external source
    content_url = Column(String(URL_LENGTH))
    is_correct = Column(Boolean, default=False)
    level = Column(Integer)

    __table_args__ = (UniqueConstraint("question_uid", "text"),)

    @property
    def session(self):
        return StoreConfig().session

    def all(self):
        return self.session.execute(select(Answer)).all()

    @classmethod
    def with_text(cls, text):
        session = StoreConfig().session
        matched_row = session.execute(select(cls).where(cls.text == text))
        return matched_row.scalar_one_or_none()

    def save(self):
        self.session.add(self)
        self.session.commit()
        return self

    def update(self, **kwargs):
        commit = kwargs.pop("commit", False)
        for k, v in kwargs.items():
            if not hasattr(self, k):
                continue
            setattr(self, k, v)

        if commit:
            self.session.commit()

    @property
    def json(self):
        return {
            "uid": self.uid,
            "text": self.text,
            "is_correct": self.is_correct,
            "position": self.position,
            "level": self.level,
            "content_url": self.content_url,
        }


class Answers:
    @classproperty
    def session(self):
        return StoreConfig().session

    @classmethod
    def count(cls):
        return cls.session.query(Answer).count()

    @classmethod
    def get(cls, uid):
        return cls.session.query(Answer).filter_by(uid=uid).one_or_none()
