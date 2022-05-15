from sqlalchemy.orm import Session

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
                )
            )
        self._session.commit()
        return self

    def questions_with_ids(self, *ids):
        return self._session.query(Question).filter(Question.uid.in_(ids))

    def update_answers(self, instance: Question, answers: list):
        for p, data in enumerate(answers):
            data.update(position=p)
            answer = instance.answers_by_uid[data["uid"]]
            self.answer_dto.update(answer, **data)

        self._session.commit()

    def update(self, instance, data: dict):
        for k, value in data.items():
            if k == "answers":
                self.update_answers(instance, value)
            elif k in ["text", "position"] and value is None:
                continue
            elif hasattr(instance, k):
                setattr(instance, k, value)

        self._session.commit()
