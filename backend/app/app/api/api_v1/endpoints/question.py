import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.domain_entities import Question
from app.domain_entities.db.session import get_db
from app.exceptions import NotFoundObjectError
from app.validation import syntax
from app.validation.logical import RetrieveObject

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
    created_question = Question(**user_input, db_session=session).save()
    return created_question


@router.put("/edit/{uid}", response_model=syntax.Question)
def edit_question(
    uid, user_input: syntax.QuestionEdit, session: Session = Depends(get_db)
):
    try:
        question = RetrieveObject(uid=uid, otype="question", db_session=session).get()
    except NotFoundObjectError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    user_input = user_input.dict()
    question.update(session, **user_input)
    return question
