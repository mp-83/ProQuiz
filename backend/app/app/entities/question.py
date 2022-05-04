from sqlalchemy import Column, ForeignKey, Integer, String, select
from sqlalchemy.orm import Session, relationship
from sqlalchemy.schema import UniqueConstraint

from app.constants import QUESTION_TEXT_MAX_LENGTH, URL_LENGTH
from app.db.base import Base
from app.db.utils import TableMixin
from app.entities.answer import Answer


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

    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    @property
    def is_open(self):
        return len(self.answers) == 0

    @property
    def answers_list(self):
        return [a.json for a in self.answers]

    @property
    def is_template(self):
        return self.game_uid is None

    def at_position(self, position):
        matched_row = self._session.execute(
            select(Question).where(Question.position == position)
        )
        return matched_row.scalar_one_or_none()

    def save(self):
        if self.position is None and self.game:
            self.position = len(self.game.questions)

        self._session.add(self)
        self._session.commit()
        self._session.refresh(self)
        return self

    def refresh(self):
        self._session.refresh(self)
        return self

    def update(self, db_session, **data):
        self._session = db_session
        for k, v in data.items():
            if k == "answers":
                self.update_answers(v)
            elif k in ["text", "position"] and v is None:
                continue
            elif hasattr(self, k):
                setattr(self, k, v)

        self._session.commit()

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

        self._session.commit()

    def create_with_answers(self, answers):
        _answers = answers or []
        self._session.add(self)
        # this commit might be avoided, as it is done in the .clone()
        # method but without it, fails
        # https://docs.sqlalchemy.org/en/14/tutorial/orm_related_objects.html#cascading-objects-into-the-session
        self._session.commit()
        for position, _answer in enumerate(_answers):
            self._session.add(
                Answer(
                    question_uid=self.uid,
                    text=_answer["text"],
                    position=position,
                    is_correct=position == 0,
                    db_session=self._session,
                )
            )
        self._session.commit()
        return self

    def clone(self, many=False):
        new = self.__class__(
            game_uid=self.game.uid if self.game else None,
            text=self.text,
            position=self.position,
        )
        self._session.add(new)
        for _answer in self.answers:
            self._session.add(
                Answer(
                    question_uid=new.uid,
                    text=_answer.text,
                    position=_answer.position,
                    is_correct=_answer.position,
                    level=_answer.level,
                )
            )
        if not many:
            self._session.commit()
        return new

    @property
    def json(self):
        return {
            "text": self.text,
            "position": self.position,
            "answers": self.answers_list,
        }


class Questions:
    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def count(self):
        return self._session.query(Question).count()

    def questions_with_ids(self, *ids):
        return self._session.query(Question).filter(Question.uid.in_(ids))

    def get(self, **filters):
        return self._session.query(Question).filter_by(**filters).one_or_none()
