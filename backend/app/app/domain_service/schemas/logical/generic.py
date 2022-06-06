from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.data_transfer.user import UserDTO
from app.exceptions import NotFoundObjectError, ValidateError


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


class LogicValidation:
    def __init__(self, schema_callable: Callable):
        self.schema_callable = schema_callable

    def validate(self, **validation_kwargs):
        try:
            return self.schema_callable(**validation_kwargs).is_valid()
        except (NotFoundObjectError, ValidateError) as exc:
            if isinstance(exc, NotFoundObjectError):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
            ) from exc
