from sqlalchemy.orm import Session

from app.domain_entities.game import Game


class GameDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = Game

    def new(self, **kwargs):
        return self.klass(**kwargs)

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()
