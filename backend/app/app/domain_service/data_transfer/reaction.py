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

    def all_reactions_of_user_to_match(self, user, match, asc=False):
        qs = self._session.query(self.klass).filter_by(user=user, match=match)
        field = Reaction.uid.asc if asc else Reaction.uid.desc
        return qs.order_by(field())  # todo to fix field
