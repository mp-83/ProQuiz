from sqlalchemy.orm import Session

from app.domain_entities.open_answer import OpenAnswer


class OpenAnswerDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = OpenAnswer

    def new(self, **kwargs) -> OpenAnswer:
        return self.klass(**kwargs)

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()
        return instance

    def get(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).one_or_none()

    def count(self):
        return self._session.query(self.klass).count()
