from sqlalchemy.orm import Session

from app.domain_entities.ranking import Ranking


class RankingDTO:
    def __init__(self, session: Session):
        self._session = session
        self.klass = Ranking

    def new(self, **kwargs) -> Ranking:
        return self.klass(**kwargs)

    def all(self):
        return self._session.query(Ranking).all()

    def add_many(self, objects: list):
        for obj in objects:
            self._session.add(obj)

        self._session.commit()

    def save(self, instance):
        self._session.add(instance)
        self._session.commit()
        return instance
