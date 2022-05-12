from datetime import datetime
from random import choices
from uuid import uuid1

from sqlalchemy import Boolean, Column, DateTime, Integer, String, select
from sqlalchemy.orm import Session

from app.constants import (
    CODE_POPULATION,
    HASH_POPULATION,
    MATCH_CODE_LEN,
    MATCH_HASH_LEN,
    MATCH_NAME_MAX_LENGTH,
    MATCH_PASSWORD_LEN,
    PASSWORD_POPULATION,
)
from app.db.base import Base
from app.db.utils import TableMixin
from app.domain_entities.game import Game
from app.domain_entities.question import Question, Questions
from app.exceptions import NotUsableQuestionError


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
    # when True games should be played in order
    order = Column(Boolean, default=True)

    def __init__(self, db_session: Session = None, **data):
        """
        Initiate the instance

        UUID based on the host ID and current time
        the first 23 chars, are the ones based on
        the time, therefore the ones that change
        every tick and guarantee the uniqueness
        """
        self._session = db_session
        expires = data.pop("expires", None)
        if not data.get("to_time"):
            self.to_time = expires

        if not data.get("from_time"):
            self.from_time = datetime.now()

        _name = data.get("name")
        if _name is None or _name == "":
            uuid_time_substring = "{}".format(uuid1())[:23]
            data["name"] = f"M-{uuid_time_substring}"

        with_code = data.pop("with_code", False)
        if with_code:
            self.code = MatchCode(db_session=self.session).get_code()

        with_hash = not with_code
        if with_hash:
            self.uhash = MatchHash(db_session=self.session).get_hash()

        if data.get("is_restricted"):
            self.uhash = (
                data.get("uhash") or MatchHash(db_session=self._session).get_hash()
            )
            self.password = MatchPassword(
                db_session=self.session, uhash=self.uhash
            ).get_value()
        super().__init__(**data)

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, v):
        self._session = v

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

    def refresh(self):
        self.session.refresh(self)
        return self

    def save(self):
        self.session.add(self)
        self.session.commit()
        # self.session.refresh(self)
        return self

    def with_name(self, name):
        matched_row = self.session.execute(select(Match).where(Match.name == name))
        return matched_row.scalar_one_or_none()

    @property
    def is_active(self):
        if self.expires:
            return (self.expires - datetime.now()).total_seconds() > 0
        return True

    @property
    def ordered_games(self):
        games = {g.index: g for g in self.games}
        _sorted = sorted(games)
        return [games[i] for i in _sorted]

    @property
    def is_started(self):
        return len(self.reactions)

    def update(self, session: Session, **attrs):
        self._session = session
        for name, value in attrs.items():
            if name == "questions":
                self.update_questions(value, commit=True)
            elif name == "name" and not value:
                continue
            else:
                setattr(self, name, value)
        self.save()

    def insert_questions(self, questions, session: Session):
        result = []
        self._session = session
        new_game = Game(match_uid=self.uid, db_session=session).save()
        for data in questions:
            question = Question(
                game_uid=new_game.uid,
                text=data.get("text"),
                position=len(new_game.questions),
                db_session=session,
            )
            question.create_with_answers(data["answers"])
            result.append(question)

        self.save()
        return result

    def update_questions(self, questions, commit=False):
        """Add or update questions for this match

        Question position is determined based on
        the position within the array
        """
        result = []
        ids = [q.get("uid") for q in questions if q.get("uid")]
        existing = {}
        if ids:
            existing = {
                q.uid: q
                for q in Questions(db_session=self._session)
                .questions_with_ids(*ids)
                .all()
            }

        for q in questions:
            game_idx = q.get("game")
            if game_idx is None:
                g = Game(match_uid=self.uid, db_session=self.session).save()
            else:
                g = self.games[game_idx]

            if q.get("uid") in existing:
                question = existing.get(q.get("uid"))
                question.text = q.get("text", question.text)
                question.position = q.get("position", question.position)
            else:
                question = Question(
                    game_uid=g.uid,
                    text=q.get("text"),
                    position=len(g.questions),
                    db_session=self.session,
                )
            self.session.add(question)
            result.append(question)

        if commit:
            self.session.commit()
        return result

    def import_template_questions(self, *ids):
        """Import already existsing questions"""
        result = []
        if not ids:
            return result

        questions = Questions(db_session=self._session).questions_with_ids(*ids).all()
        new_game = Game(match_uid=self.uid, db_session=self._session).save()
        for question in questions:
            if question.game_uid:
                raise NotUsableQuestionError(
                    f"Question with id {question.uid} is already in use"
                )

            new = Question(
                game_uid=new_game.uid,
                text=question.text,
                position=question.position,
                db_session=self._session,
            )
            self.session.add(new)
            result.append(new)
        self.session.commit()
        return result

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
            "name": self.name,
            "is_restricted": self.is_restricted,
            "expires": self.expires.isoformat() if self.to_time else None,
            "order": self.order,
            "times": self.times,
            "code": self.code,
            "uhash": self.uhash,
            "questions": [[q.json for q in g.ordered_questions] for g in self.games],
        }

    def set_hash(self, value):
        self.uhash = value
        self.save()
        return self


class MatchHash:
    def __init__(self, db_session: Session):
        self._session = db_session

    def new_value(self, length):
        return "".join(choices(HASH_POPULATION, k=length))

    def get_hash(self, length=MATCH_HASH_LEN):
        value = self.new_value(length)
        while Matches(db_session=self._session).get(uhash=value):
            value = self.new_value(length)

        return value


class MatchPassword:
    def __init__(self, db_session, uhash):
        self._session = db_session
        self.match_uhash = uhash

    def new_value(self, length):
        return "".join(choices(PASSWORD_POPULATION, k=length))

    def get_value(self, length=MATCH_PASSWORD_LEN):
        value = self.new_value(length)
        while Matches(db_session=self._session).get(
            uhash=self.match_uhash, password=value
        ):
            value = self.new_value(length)

        return value


class MatchCode:
    def __init__(self, db_session: Session):
        self._session = db_session

    def new_value(self, length):
        return "".join(choices(CODE_POPULATION, k=length))

    def get_code(self, length=MATCH_CODE_LEN):
        value = self.new_value(length)
        while Matches(db_session=self._session).active_with_code(value):
            value = self.new_value(length)

        return value


class Matches:
    def __init__(self, db_session: Session):
        self._session = db_session

    def count(self):
        return self._session.query(Match).count()

    def get(self, **filters):
        return self._session.query(Match).filter_by(**filters).one_or_none()

    def active_with_code(self, code):
        return (
            self._session.query(Match)
            .filter(Match.code == code, Match.to_time > datetime.now())
            .one_or_none()
        )

    def all_matches(self, **filters):
        return self._session.query(Match).filter_by(**filters).all()
