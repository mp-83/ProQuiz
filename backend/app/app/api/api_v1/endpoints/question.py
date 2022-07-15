import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain_entities.db.session import get_db
from app.domain_entities.user import User
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.schemas import response
from app.domain_service.schemas import syntax_validation as syntax
from app.domain_service.schemas.logical_validation import (
    LogicValidation,
    RetrieveObject,
    ValidateNewQuestion,
)
from app.exceptions import NotFoundObjectError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=response.ManyQuestions)
def list_questions(
    request: Request,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filters = request.query_params
    all_questions = QuestionDTO(session=session).all_questions(**filters)
    return {"questions": all_questions}


@router.get("/{uid}", response_model=response.Question)
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


@router.post("/new", response_model=response.Question)
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


@router.put("/edit/{uid}", response_model=response.Question)
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

    validated_data = question_in.dict()
    _initial_fields = validated_data.pop("_initial_fields")
    fields_to_update = {f: v for f, v in validated_data.items() if f in _initial_fields}
    dto = QuestionDTO(session=session)
    dto.update(question, fields_to_update)
    return question
