from app.constants import QUESTION_TEXT_MAX_LENGTH, URL_LENGTH
from app.entities.answer import Answer
from app.db.base import Base
from app.db.utils import StoreConfig, TableMixin, classproperty
from sqlalchemy import Column, ForeignKey, Integer, String, select
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint


class Question(TableMixin, Base):
    __tablename__ = "questions"

    game_uid = Column(Integer, ForeignKey("games.uid", ondelete="SET NULL"))
    game = relationship("Game", backref="questions")
    # reactions: implicit backward relation

    text = Column(String(QUESTION_TEXT_MAX_LENGTH), nullable=False)
    position = Column(Integer, nullable=False)
    time = Column(Integer)  # in seconds
    content_url = Column(String(URL_LENGTH))

    __table_args__ = (
        UniqueConstraint("game_uid", "position", name="ck_question_game_uid_position"),
    )

    @property
    def session(self):
        return StoreConfig().session

    @property
    def is_open(self):
        return len(self.answers) == 0

    @property
    def is_template(self):
        return self.game_uid is None

    def all(self):
        return self.session.execute(select(Question)).all()

    def at_position(self, position):
        matched_row = self.session.execute(
            select(Question).where(Question.position == position)
        )
        return matched_row.scalar_one_or_none()

    def save(self):
        if self.position is None and self.game:
            self.position = len(self.game.questions)

        self.session.add(self)
        self.session.commit()
        return self

    def refresh(self):
        self.session.refresh(self)
        return self

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if k == "answers":
                self.update_answers(v)
            elif hasattr(self, k):
                setattr(self, k, v)

        self.session.commit()

    @property
    def answers_by_uid(self):
        return {a.uid: a for a in self.answers}

    @property
    def answers_by_position(self):
        return {a.position: a for a in self.answers}

    def update_answers(self, answers):
        for p, data in enumerate(answers):
            data.update(position=p)
            _answer = self.answers_by_uid[data["uid"]]
            _answer.update(**data)

        self.session.commit()

    def create_with_answers(self, answers):
        _answers = answers or []
        self.session.add(self)
        # this commit might be avoided, as it is done in the .clone()
        # method but without it, fails
        # https://docs.sqlalchemy.org/en/14/tutorial/orm_related_objects.html#cascading-objects-into-the-session
        self.session.commit()
        for position, _answer in enumerate(_answers):
            self.session.add(
                Answer(
                    question_uid=self.uid,
                    text=_answer["text"],
                    position=position,
                    is_correct=position == 0,
                )
            )
        self.session.commit()
        return self

    def clone(self, many=False):
        new = self.__class__(
            game_uid=self.game.uid if self.game else None,
            text=self.text,
            position=self.position,
        )
        self.session.add(new)
        for _answer in self.answers:
            self.session.add(
                Answer(
                    question_uid=new.uid,
                    text=_answer.text,
                    position=_answer.position,
                    is_correct=_answer.position,
                    level=_answer.level,
                )
            )
        if not many:
            self.session.commit()
        return new

    @property
    def json(self):
        return {
            "text": self.text,
            "position": self.position,
            "answers": [a.json for a in self.answers],
        }


class Questions:
    @classproperty
    def session(self):
        return StoreConfig().session

    @classmethod
    def count(cls):
        return cls.session.query(Question).count()

    @classmethod
    def questions_with_ids(cls, *ids):
        return cls.session.query(Question).filter(Question.uid.in_(ids))

    @classmethod
    def get(cls, **filters):
        return cls.session.query(Question).filter_by(**filters).one_or_none()
