from sqlalchemy.orm import Session

from app.domain_entities.game import Game
from app.domain_entities.question import Question
from app.domain_service.data_transfer.answer import AnswerDTO


class QuestionDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = Question
        self.answer_dto = AnswerDTO(session=session)

    def new(self, **kwargs):
        return self.klass(**kwargs)

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()
        return instance

    def add_many(self, objects):
        self._session.add_all(objects)
        self._session.commit()
        return objects

    def all_questions(self, **filters):
        match_uid = filters.get("match_uid")
        base_query = self._session.query(self.klass)
        if match_uid:
            base_query = base_query.join(Game, Game.uid == Question.game_uid).filter(
                Game.match_uid == match_uid
            )

        return base_query.filter_by(**filters).all()

    def at_position(self, position):
        return (
            self._session.query(self.klass).filter_by(position=position).one_or_none()
        )

    def get(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).one_or_none()

    def count(self):
        return self._session.query(self.klass).count()

    def create_with_answers(self, question, answers):
        _answers = answers or []
        self._session.add(question)
        # this commit might be avoided, as it is done in the .clone()
        # method but without it, fails
        # https://docs.sqlalchemy.org/en/14/tutorial/orm_related_objects.html#cascading-objects-into-the-session
        self._session.commit()
        for position, _answer in enumerate(_answers):
            self._session.add(
                self.answer_dto.new(
                    question_uid=question.uid,
                    text=_answer["text"],
                    position=position,
                    is_correct=position == 0,
                    boolean=question.boolean,
                )
            )
        self._session.commit()
        return self

    def questions_with_ids(self, *ids):
        return self._session.query(Question).filter(Question.uid.in_(ids))

    def create_or_update_answers(self, instance: Question, answers: list):
        for n, answer_data in enumerate(answers, start=len(instance.answers)):
            answer = instance.answers_by_uid.get(answer_data.get("uid"))
            answer_data.update(question_uid=instance.uid, position=n)
            if answer:
                answer = self.answer_dto.update(answer, **answer_data)
            else:
                answer_data.update(is_correct=n == 0)
                answer = self.answer_dto.new(**answer_data)
            self._session.add(answer)

    def update_answers(self, instance: Question, answers: list):
        if not answers:
            return

        for data in answers:
            answer = instance.answers_by_uid[data["uid"]]
            self.answer_dto.update(answer, **data)

        self._session.commit()

    def reorder_answers(self, instance: Question, answers_ids: list):
        for p, uid in enumerate(answers_ids):
            answer = instance.answers_by_uid[uid]
            answer.position = p

        self._session.commit()

    def update(self, instance: Question, data: dict):
        answers = data.pop("answers", [])
        for k, value in data.items():
            if k == "text" and value is None:
                if data.get("content_url") is None:
                    continue
                value = "ContentURL"
            if k == "position" and value is None:
                continue
            elif hasattr(instance, k):
                setattr(instance, k, value)

        if data.get("reorder"):
            self.reorder_answers(instance, [a["uid"] for a in answers])
        else:
            self.update_answers(instance, answers)
        self.save(instance)

    def clone(self, instance: Question, many=False):
        new = self.klass(
            game_uid=instance.game.uid if instance.game else None,
            text=instance.text,
            position=instance.position,
        )
        self.save(new)
        for _answer in instance.answers:
            self._session.add(
                self.answer_dto.new(
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
