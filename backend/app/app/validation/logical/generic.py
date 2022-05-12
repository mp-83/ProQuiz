from sqlalchemy.orm import Session

from app.domain_entities import Answers, Matches, Questions, Users
from app.exceptions import NotFoundObjectError


class RetrieveObject:
    def __init__(self, uid: int, otype: str, db_session: Session):
        self.object_uid = uid
        self.otype = otype
        self.db_session = db_session

    def get(self):
        klass = {
            "answer": Answers,
            "match": Matches,
            "question": Questions,
            "user": Users,
        }.get(self.otype)

        obj = klass(self.db_session).get(uid=self.object_uid)
        if obj:
            return obj
        raise NotFoundObjectError()
