from sqlalchemy.orm import Session

from app.domain_entities.ranking import Ranking


class RankingDTO:
    def __init__(self, session: Session):
        self._session = session

    def of_match(self, match_uid):
        return self._session.query(Ranking).filter_by(match_uid=match_uid).all()

    def all(self):
        return self._session.query(Ranking).all()

    def add_many(self, objects: list):
        for obj in objects:
            self._session.add(obj)

        self._session.commit()
