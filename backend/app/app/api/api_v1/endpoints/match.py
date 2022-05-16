import logging

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import login_required
from app.domain_entities.db.session import get_db
from app.domain_entities.user import User
from app.domain_service.data_transfer.answer import AnswerDTO
from app.domain_service.data_transfer.game import GameDTO
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.data_transfer.question import QuestionDTO
from app.domain_service.validation import syntax
from app.domain_service.validation.logical import (
    RetrieveObject,
    ValidateEditMatch,
    ValidateMatchImport,
)
from app.exceptions import NotFoundObjectError, ValidateError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def list_matches(
    session: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    # TODO: to fix the filtering parameters
    all_matches = MatchDTO(session=session).all_matches(**{})
    return {"matches": [m.json for m in all_matches]}


@router.get("/{uid}", response_model=syntax.Match)
def get_match(
    uid: int,
    session: Session = Depends(get_db),
):
    try:
        match = RetrieveObject(uid=uid, otype="match", db_session=session).get()
    except NotFoundObjectError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    return match


@router.post("/new", response_model=syntax.Match)
def create_match(
    user_input: syntax.MatchCreate,
    session: Session = Depends(get_db),
):
    user_input = user_input.dict()
    questions = user_input.pop("questions", None) or []
    dto = MatchDTO(session=session)
    new_match = dto.new(**user_input)
    dto.save(new_match)

    game_dto = GameDTO(session=session)
    new_game = game_dto.new(match_uid=new_match.uid)
    game_dto.save(new_game)
    question_dto = QuestionDTO(session=session)
    answer_dto = AnswerDTO(session=session)
    for position, question in enumerate(questions):
        new = question_dto.new(
            game_uid=new_game.uid,
            text=question["text"],
            position=position,
        )
        question_dto.save(new)

        for p, _answer in enumerate(question.get("answers") or []):
            session.add(
                answer_dto.new(
                    question_uid=new.uid,
                    text=_answer["text"],
                    position=p,
                    is_correct=position == 0,
                )
            )

    session.commit()
    session.refresh(new_match)
    return new_match


@login_required
@router.put("/edit/{uid}", response_model=syntax.Match)
def edit_match(
    uid: int,
    user_input: syntax.MatchEdit,
    session: Session = Depends(get_db),
):
    try:
        match = ValidateEditMatch(uid, db_session=session).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": e.message}
        )

    user_input = user_input.dict()
    dto = MatchDTO(session=session)
    dto.update(match, **user_input)
    return match


@login_required
@router.post("/yaml_import", response_model=syntax.Match)
def match_yaml_import(
    user_input: syntax.MatchYamlImport,
    session: Session = Depends(get_db),
):
    user_input = user_input.dict()
    match_uid = user_input.get("uid")

    try:
        match = ValidateMatchImport(match_uid, db_session=session).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": e.message}
        )

    dto = MatchDTO(session=session)
    dto.insert_questions(match, user_input["data"]["questions"])
    return match
