from sqlalchemy.orm import Session

from app.domain_entities.answer import Answer


class AnswerDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = Answer

    def new(self, **kwargs):
        return self.klass(**kwargs)

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()

    def count(self):
        return self._session.query(self.klass).count()

    def get(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).one_or_none()

    def update(self, instance, **kwargs):
        commit = kwargs.pop("commit", False)
        for k, v in kwargs.items():
            if not hasattr(instance, k):
                continue
            setattr(instance, k, v)

        if commit:
            self._session.commit()
