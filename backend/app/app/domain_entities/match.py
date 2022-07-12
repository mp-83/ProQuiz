from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.constants import (
    MATCH_CODE_LEN,
    MATCH_HASH_LEN,
    MATCH_NAME_MAX_LENGTH,
    MATCH_PASSWORD_LEN,
)
from app.domain_entities.db.base import Base
from app.domain_entities.db.utils import TableMixin


class Match(TableMixin, Base):
    __tablename__ = "matches"

    # implicit backward relations
    # games: rankings: reactions:

    name = Column(String(MATCH_NAME_MAX_LENGTH), nullable=False, unique=True)
    # unique hash identifying this match
    uhash = Column(String(MATCH_HASH_LEN))
    # code needed to start match
    code = Column(String(MATCH_CODE_LEN))
    # password needed to start the match if it's restricted
    password = Column(String(MATCH_PASSWORD_LEN))
    # designates the accessibility to this match
    is_restricted = Column(Boolean, default=True)
    # determine the time range the match is playable
    from_time = Column(DateTime(timezone=True))
    to_time = Column(DateTime(timezone=True))
    # how many times a match can be played
    times = Column(Integer, default=1)
    # indicates if games should be played in order
    order = Column(Boolean, default=True)

    @property
    def questions(self):
        return [g.ordered_questions for g in self.games]

    @property
    def questions_list(self):
        return [q for g in self.games for q in g.ordered_questions]
        # return [[q.json for q in g.ordered_questions] for g in self.games]

    @property
    def questions_count(self):
        return sum(len(g.questions) for g in self.games)

    @property
    def expires(self):
        return self.to_time

    @property
    def is_active(self):
        if self.expires:
            # TODO to better fix. now should be tz aware all the times
            # to investigate why SQL does not save timezone aware datetime
            now = (
                datetime.now(tz=timezone.utc) if self.expires.tzinfo else datetime.now()
            )
            return (self.expires - now).total_seconds() > 0
        return True

    @property
    def ordered_games(self):
        games = {g.index: g for g in self.games}
        _sorted = sorted(games)
        return [games[i] for i in _sorted]

    @property
    def is_started(self):
        return len(self.reactions)

    # TODO: to fix. It should not count the reaction but the number of completed
    # attempts for this match.
    def left_attempts(self, user):
        return len([r for r in self.reactions if r.user.uid == user.uid]) - self.times

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
            "questions": [[q.json for q in g.ordered_questions] for g in self.games],
        }
