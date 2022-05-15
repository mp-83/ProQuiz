from sqlalchemy import Column, ForeignKey, Integer, String, select
from sqlalchemy.orm import Session, relationship
from sqlalchemy.schema import UniqueConstraint

from app.constants import QUESTION_TEXT_MAX_LENGTH, URL_LENGTH
from app.domain_entities.answer import Answer
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


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

    def __init__(self, db_session: Session = None, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def set_session(self, s):
        self._session = s

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
        return self

    def refresh(self):
        self._session.refresh(self)
        return self

    def update(self, db_session, **data):
        pass

    @property
    def answers_by_uid(self):
        return {a.uid: a for a in self.answers}

    @property
    def answers_by_position(self):
        return {a.position: a for a in self.answers}

    def update_answers(self, answers):
        pass

    def create_with_answers(self, answers):
        pass

    def clone(self, many=False):
        new = self.__class__(
            game_uid=self.game.uid if self.game else None,
            text=self.text,
            position=self.position,
            db_session=self._session,
        ).save()
        for _answer in self.answers:
            self._session.add(
                Answer(
                    question_uid=new.uid,
                    text=_answer.text,
                    position=_answer.position,
                    is_correct=_answer.position,
                    level=_answer.level,
                    db_session=self._session,
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
