import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.domain_entities.db.session import get_db
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.validation import syntax
from app.domain_service.validation.logical import RetrieveObject
from app.exceptions import NotFoundObjectError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{uid}", response_model=syntax.Question)
def get_question(uid: int, session: Session = Depends(get_db)):
    try:
        question = RetrieveObject(uid=uid, otype="question", db_session=session).get()
    except NotFoundObjectError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    return question


@router.post("/new", response_model=syntax.Question)
def new_question(user_input: syntax.QuestionCreate, session: Session = Depends(get_db)):
    user_input = user_input.dict()
    dto = QuestionDTO(session=session)
    instance = dto.new(**user_input)
    return dto.save(instance)


@router.put("/edit/{uid}", response_model=syntax.Question)
def edit_question(
    uid, user_input: syntax.QuestionEdit, session: Session = Depends(get_db)
):
    try:
        question = RetrieveObject(uid=uid, otype="question", db_session=session).get()
    except NotFoundObjectError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    user_input = user_input.dict()
    dto = QuestionDTO(session=session)
    dto.update(question, **user_input)
    return question