from datetime import datetime, timezone

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

        self._session.add(instance)
        self._session.commit()
        return instance

    def count(self):
        return self._session.query(self.klass).count()

    def all_reactions_of_user_to_match(self, user, match, question=None, asc=False):
        filters = {"user": user, "match": match}
        if question:
            filters.update(question=question)
        qs = self._session.query(self.klass).filter_by(**filters)
        field = Reaction.uid.asc if asc else Reaction.uid.desc
        return qs.order_by(field())

    def record_answer(self, instance, answer):
        """Save the answer given by the user

        If question is expired discard the answer
        Store the answer for bot, open or timed
        questions.
        """
        response_datetime = datetime.now(tz=timezone.utc)
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
        if question_expired:
            return instance

        if answer:
            rs = ReactionScore(
                response_time_in_secs, instance.question.time, answer.level
            )
            instance.score = rs.value()

        instance.update_timestamp = response_datetime
        if answer:
            instance.answer_time = instance.update_timestamp
            if instance.question.is_open:
                instance.open_answer_uid = answer.uid
            else:
                instance.answer_uid = answer.uid

        return self.save(instance)

    def reaction_of_user_to_question(self, user, question):
        return (
            self._session.query(Reaction)
            .filter_by(user=user, question=question)
            .one_or_none()
        )


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
