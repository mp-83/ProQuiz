import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain_entities.db.session import get_db
from app.domain_entities.user import User
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.schemas import syntax
from app.domain_service.schemas.logical import (
    LogicValidation,
    RetrieveObject,
    ValidateNewQuestion,
)
from app.exceptions import NotFoundObjectError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=syntax.ManyQuestions)
def list_questions(
    request: Request,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filters = request.query_params
    all_questions = QuestionDTO(session=session).all_questions(**filters)
    return {"questions": all_questions}


@router.get("/{uid}", response_model=syntax.Question)
def get_question(
    uid: int,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        question = RetrieveObject(uid=uid, otype="question", db_session=session).get()
    except NotFoundObjectError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc

    return question


@router.post("/new", response_model=syntax.Question)
def new_question(
    question_in: syntax.QuestionCreate,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    user_input = question_in.dict()
    LogicValidation(ValidateNewQuestion).validate(question_in=user_input)
    dto = QuestionDTO(session=session)
    answers = user_input.pop("answers", [])
    new_instance = dto.new(**user_input)
    dto.create_with_answers(new_instance, answers=answers)
    return dto.save(new_instance)


@router.put("/edit/{uid}", response_model=syntax.Question)
def edit_question(
    uid,
    question_in: syntax.QuestionEdit,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        question = RetrieveObject(uid=uid, otype="question", db_session=session).get()
    except NotFoundObjectError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc

    dto = QuestionDTO(session=session)
    dto.update(question, question_in.dict())
    return question
