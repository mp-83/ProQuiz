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
        return instance

    def get(self, **filters):
        return self._session.query(self.klass).filter_by(**filters).one_or_none()

    def refresh(self, instance):
        self._session.refresh(instance)
        return instance

    def nullable_column(self, name):
        return self.klass.__table__.columns.get(name).nullable

    def update(self, instance, **kwargs):
        commit = kwargs.pop("commit", False)
        for k, v in kwargs.items():
            if k == "uid":
                continue

            if not hasattr(instance, k) or (v is None and not self.nullable_column(k)):
                continue
            setattr(instance, k, v)

        if commit:
            self._session.commit()
