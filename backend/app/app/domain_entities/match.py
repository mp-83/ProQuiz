from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, text
from sqlalchemy.orm import relationship

from app.constants import (
    MATCH_CODE_LEN,
    MATCH_HASH_LEN,
    MATCH_NAME_MAX_LENGTH,
    MATCH_PASSWORD_LEN,
    TOPIC_NAME_LENGTH,
)
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import QAppenderClass, TableMixin


class Match(TableMixin, Base):
    __tablename__ = "matches"

    name = Column(String(MATCH_NAME_MAX_LENGTH), nullable=False, unique=True)
    # unique hash identifying this match
    uhash = Column(String(MATCH_HASH_LEN))
    # code needed to start match
    code = Column(String(MATCH_CODE_LEN))
    # password needed to start the match if it's restricted
    password = Column(String(MATCH_PASSWORD_LEN))
    # designates the accessibility to this match
    is_restricted = Column(Boolean, server_default="0")
    # determine the time range the match is playable
    from_time = Column(DateTime)
    to_time = Column(DateTime)
    # how many times a match can be played. times = 0 means unlimited times
    times = Column(Integer, server_default=text("1"))
    # indicates if games should be played in order
    order = Column(Boolean, server_default="1")
    topic = Column(String(TOPIC_NAME_LENGTH))
    # indicates whether the user has to be told that the answer given
    # (if any) was the correct one
    notify_correct = Column(Boolean, server_default="0")
    # indicates whether this match is a treasure hunt, that
    # implies the next question is returned only if the previous
    # one was answered correctly
    treasure_hunt = Column(Boolean, server_default="0")

    games = relationship(
        "Game",
        viewonly=True,
        order_by="Game.index",
        lazy="dynamic",
        query_class=QAppenderClass,
    )
    reactions = relationship(
        "Reaction",
        viewonly=True,
        order_by="Reaction.uid",
        lazy="dynamic",
        query_class=QAppenderClass,
    )
    rankings = relationship(
        "Ranking",
        viewonly=True,
        order_by="Ranking.uid",
        lazy="dynamic",
        query_class=QAppenderClass,
    )

    @property
    def questions(self):
        return [g.questions.all() for g in self.games]

    @property
    def questions_list(self):
        """
        Return all questions of the match
        """
        return [q for g in self.games for q in g.questions.all()]

    @property
    def games_list(self):
        return self.games.all()

    @property
    def questions_count(self):
        return sum(g.questions.count() for g in self.games)

    @property
    def expires(self):
        return self.to_time

    @property
    def is_open(self):
        return all(q.is_open for g in self.games for q in g.questions.all())

    @property
    def is_active(self):
        if self.expires:
            now = datetime.now() if self.expires.tzinfo else datetime.now()
            return (self.expires - now).total_seconds() > 0
        return True

    @property
    def is_started(self):
        return self.reactions.count()

    def left_attempts(self, user):
        if self.times == 0:
            return 1
        return (
            self.times
            - self.reactions.filter_by(user_uid=user.uid)
            .filter_join(position=0)
            .count()
        )

    @property
    def open_answers(self):
        return [r.answer for r in self.reactions.filter_by(open_answer_uid__isnot=None)]

    @property
    def json(self):
        """
        Store questions as list, one per game
        """
        return {
            "uid": self.uid,
            "name": self.name,
            "is_restricted": self.is_restricted,
            "password": self.password,
            "expires": self.expires.isoformat() if self.to_time else None,
            "order": self.order,
            "times": self.times,
            "code": self.code,
            "uhash": self.uhash,
            "questions": [[q.json for q in g.questions] for g in self.games],
        }
