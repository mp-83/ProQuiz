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
