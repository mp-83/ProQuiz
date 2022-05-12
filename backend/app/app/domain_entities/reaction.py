from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Session, relationship
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
    # this column might be saved as the game might be fetched via the question
    # TODO: open point, keep or remove it
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

    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    @property
    def session(self):
        return self._session

    @property
    def answer(self):
        return self._open_answer if self.question.is_open else self._answer

    def refresh(self):
        self.session.refresh(self)
        return self

    def save(self):
        if not self.game_uid:
            self.game_uid = self.question.game.uid
        self.session.add(self)
        self.session.commit()
        return self

    def record_answer(self, answer):
        """Save the answer given by the user

        If question is expired discard the answer
        Store the answer for bot, open or timed
        questions.
        """
        response_datetime = datetime.now(tz=timezone.utc)
        if not self.create_timestamp.tzinfo:
            self.create_timestamp = self.create_timestamp.replace(
                tzinfo=response_datetime.tzinfo
            )

        response_time_in_secs = (
            response_datetime - self.create_timestamp
        ).total_seconds()
        question_expired = (
            self.question.time is not None
            and self.question.time - response_time_in_secs < 0
        )
        if question_expired:
            return self

        rs = ReactionScore(response_time_in_secs, self.question.time, answer.level)
        self.score = rs.value()

        # TODO to fix. The update_timestamp should be updated via handler
        self.update_timestamp = response_datetime
        if self.question.is_open:
            self.open_answer_uid = answer.uid
        else:
            self.answer_uid = answer.uid
        self.answer_time = self.update_timestamp
        self.session.commit()
        return self

    @property
    def json(self):
        return {}


class ReactionScore:
    def __init__(self, timing, question_time=None, answer_level=None):
        self.timing = timing
        self.question_time = question_time
        self.answer_level = answer_level

    def value(self):
        if not self.question_time:
            return 0

        v = self.question_time - self.timing
        v = v / self.question_time
        if self.answer_level:
            v *= self.answer_level
        return round(v, 3)


class Reactions:
    def __init__(self, db_session: Session, **kwargs):
        self._session = db_session
        super().__init__(**kwargs)

    def count(self):
        return self._session.query(Reaction).count()

    def reaction_of_user_to_question(self, user, question):
        return (
            self._session.query(Reaction)
            .filter_by(user=user, question=question)
            .one_or_none()
        )

    def all_reactions_of_user_to_match(self, user, match, asc=False):
        qs = self._session.query(Reaction).filter_by(user=user, match=match)
        field = Reaction.uid.asc if asc else Reaction.uid.desc
        return qs.order_by(field())
