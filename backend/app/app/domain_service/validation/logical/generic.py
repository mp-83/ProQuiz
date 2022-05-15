from sqlalchemy.orm import Session

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.user import UserDTO
from app.exceptions import NotFoundObjectError


class RetrieveObject:
    def __init__(self, uid: int, otype: str, db_session: Session):
        self.object_uid = uid
        self.otype = otype
        self.db_session = db_session

    def get(self):
        klass = {
            "answer": AnswerDTO,
            "match": MatchDTO,
            "question": QuestionDTO,
            "user": UserDTO,
        }.get(self.otype)

        obj = klass(self.db_session).get(uid=self.object_uid)
        if obj:
            return obj
        raise NotFoundObjectError()
