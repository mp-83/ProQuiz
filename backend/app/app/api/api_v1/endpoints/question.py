import logging

from app.entities import Question
from app.exceptions import NotFoundObjectError
from app.core.security import login_required
from app.validation.logical import RetrieveObject
from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter()


@login_required
@router.get("/{uid}")
def get_question(uid: int, response: Response):
    try:
        question = RetrieveObject(uid=uid, otype="question").get()
    except NotFoundObjectError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    return question.json


@login_required
@router.post("/new")
def new_question(user_input):
    created_question = Question(**user_input).save()
    return created_question.json


@login_required
@router.put("/edit/{uid}")
def edit_question(uid, user_input, response: Response):
    try:
        question = RetrieveObject(uid=uid, otype="question").get()
    except NotFoundObjectError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    question.update(**user_input)
    return question.json
