from datetime import datetime
from random import choices
from typing import List
from uuid import uuid1

from sqlalchemy.orm import Session

from app.constants import (
    CODE_POPULATION,
    HASH_POPULATION,
    MATCH_CODE_LEN,
    MATCH_HASH_LEN,
    MATCH_PASSWORD_LEN,
    PASSWORD_POPULATION,
)
from app.domain_entities.match import Match
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.exceptions import NotUsableQuestionError


class MatchDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = Match
        self.game_dto = GameDTO(session=session)
        self.question_dto = QuestionDTO(session=session)

    def new(self, **kwargs):
        """
        Initiate the instance

        UUID based on the host ID and current time
        the first 23 chars, are the ones based on
        the time, therefore the ones that change
        every tick and guarantee the uniqueness
        """
        expires = kwargs.pop("expires", None)
        with_code = kwargs.pop("with_code", False)

        instance = self.klass(**kwargs)
        if not instance.to_time:
            instance.to_time = expires

        if not instance.from_time:
            instance.from_time = datetime.now()

        if not instance.name:
            uuid_time_substring = "{}".format(uuid1())[:23]
            instance.name = f"M-{uuid_time_substring}"

        if with_code:
            instance.code = MatchCode(db_session=self._session).get_code()

        with_hash = not with_code
        if with_hash:
            instance.uhash = MatchHash(db_session=self._session).get_hash()

        if kwargs.get("is_restricted"):
            instance.uhash = (
                kwargs.get("uhash") or MatchHash(db_session=self._session).get_hash()
            )
            instance.password = MatchPassword(
                db_session=self._session, uhash=instance.uhash
            ).get_value()

        return instance

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()
        return instance

    def refresh(self, instance):
        self._session.refresh(instance)
        return instance

    def get(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).one_or_none()

    def active_with_code(self, code):
        return (
            self._session.query(self.klass)
            .filter(Match.code == code, Match.to_time > datetime.now())
            .one_or_none()
        )

    def update_questions(self, instance: Match, questions: list, commit=False):
        """Add or update questions for this match

        Question position is determined based on
        the position within the array
        """
        result = []
        ids = [q.get("uid") for q in questions if q.get("uid")]
        existing = {}
        if ids:
            existing = {
                q.uid: q for q in self.question_dto.questions_with_ids(*ids).all()
            }

        for question_data in questions:
            game_no = question_data.get("game")
            game = instance.games[game_no] if game_no else instance.games[0]

            if question_data.get("uid") in existing:
                question = existing.get(question_data.get("uid"))
                question.text = question_data.get("text", question.text)
                question.position = question_data.get("position", question.position)
            else:
                question = self.question_dto.new(
                    game_uid=game.uid,
                    text=question_data.get("text"),
                    position=len(game.questions),
                )
            self.question_dto.save(question)
            self.question_dto.create_or_update_answers(
                question, question_data.get("answers", [])
            )
            result.append(question)

        if commit:
            self._session.commit()
        return result

    def import_template_questions(self, instance: Match, ids: List, game_uid=None):
        """Import already existing questions"""
        result = []
        if not ids:
            return result

        questions = self.question_dto.questions_with_ids(*ids).all()
        new_game = self.game_dto.get(uid=game_uid) or self.game_dto.save(
            self.game_dto.new(match_uid=instance.uid, index=len(instance.games))
        )
        for question in questions:
            if question.game_uid:
                raise NotUsableQuestionError(
                    f"Question with id {question.uid} is already in use"
                )

            new = self.question_dto.new(
                game_uid=new_game.uid,
                text=question.text,
                position=question.position,
            )
            self._session.add(new)
            result.append(new)
        self._session.commit()
        return result

    def all_matches(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).all()

    def nullable_column(self, name):
        return self.klass.__table__.columns.get(name).nullable

    def update(self, instance: Match, **attrs):
        for name, value in attrs.items():
            if name == "questions":
                self.update_questions(instance, value, commit=True)
            elif not hasattr(instance, name) or (
                value is None and not self.nullable_column(name)
            ):
                continue
            else:
                setattr(instance, name, value)
        self.save(instance)

    def _boolean_answers(self, answers_list: List) -> bool:
        return [a["text"] for a in answers_list] == [True, False]

    def insert_questions(self, instance, questions: list):
        result = []
        game_dto = GameDTO(session=self._session)
        new_game = game_dto.new(match_uid=instance.uid)
        game_dto.save(new_game)

        question_dto = QuestionDTO(session=self._session)
        for data in questions:
            boolean_question = self._boolean_answers(data["answers"])
            new_q_instance = question_dto.new(
                game_uid=new_game.uid,
                text=data.get("text"),
                position=len(new_game.questions),
                boolean=boolean_question,
            )
            question_dto.create_with_answers(new_q_instance, data["answers"])
            result.append(new_q_instance)

        self._session.commit()
        return result


class MatchHash:
    def __init__(self, db_session: Session):
        self._session = db_session

    def new_value(self, length):
        return "".join(choices(HASH_POPULATION, k=length))

    def get_hash(self, length=MATCH_HASH_LEN):
        value = self.new_value(length)
        while MatchDTO(session=self._session).get(uhash=value):
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
        while MatchDTO(session=self._session).get(
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
        while MatchDTO(session=self._session).active_with_code(value):
            value = self.new_value(length)

        return value
