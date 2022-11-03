from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain_entities.reaction import Reaction


class ReactionDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = Reaction

    def new(self, **kwargs):
        return self.klass(**kwargs)

    def save(self, instance):
        if not instance.game_uid:
            instance.game_uid = instance.question.game.uid

        if not instance.attempt_uid:
            instance.attempt_uid = uuid4().hex

        self._session.add(instance)
        self._session.commit()
        return instance

    def record_answer(self, instance, answer=None, open_answer=None) -> bool:
        """Save the answer given by the user

        If question is expired discard the answer
        Store the answer for bot, open or timed
        questions.
        """
        was_correct = False
        response_datetime = datetime.now(tz=timezone.utc)
        assert not instance.update_timestamp
        if not instance.create_timestamp.tzinfo:
            instance.create_timestamp = instance.create_timestamp.replace(
                tzinfo=response_datetime.tzinfo
            )

        response_time_in_secs = (
            response_datetime - instance.create_timestamp
        ).total_seconds()
        question_expired = (
            instance.question.time is not None
            and instance.question.time - response_time_in_secs < 0
        )
        instance.update_timestamp = response_datetime
        if question_expired:
            self.save(instance)
            return was_correct

        if answer:
            rs = ReactionScore(
                response_time_in_secs, instance.question.time, answer.level
            )
            instance.score = rs.value()

        if answer or open_answer:
            instance.answer_time = instance.update_timestamp
            if open_answer:
                instance.open_answer_uid = open_answer.uid
            else:
                instance.answer_uid = answer.uid
                was_correct = answer.is_correct
            self.save(instance)

        return was_correct


class ReactionScore:
    def __init__(self, timing, question_time=None, answer_level=None):
        self.timing = timing
        self.question_time = question_time
        self.answer_level = answer_level

    def value(self):
        if not self.question_time:
            return self.answer_level or 0

        v = self.question_time - self.timing
        v = v / self.question_time
        if self.answer_level:
            v *= self.answer_level
        return round(v, 3)
