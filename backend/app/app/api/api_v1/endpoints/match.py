import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain_entities.db.session import get_db
from app.domain_entities.user import User
from app.domain_service.data_transfer.match import MatchDTO
from app.domain_service.schemas import response
from app.domain_service.schemas import syntax_validation as syntax
from app.domain_service.schemas.logical_validation import (
    LogicValidation,
    RetrieveObject,
    ValidateEditMatch,
    ValidateMatchImport,
    ValidateNewMatch,
)
from app.exceptions import NotFoundObjectError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=response.Matches)
def list_matches(
    session: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    all_matches = MatchDTO(session=session).all_matches(**{})
    return {"matches": all_matches}


@router.get("/{uid}", response_model=response.Match)
def get_match(
    uid: int,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        match = RetrieveObject(uid=uid, otype="match", db_session=session).get()
    except NotFoundObjectError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc

    return match


@router.post("/new", response_model=response.Match)
def create_match(
    match_in: syntax.MatchCreate,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    user_input = match_in.dict()
    LogicValidation(ValidateNewMatch).validate(match_in=user_input, db_session=session)
    questions = user_input.pop("questions", None) or []
    dto = MatchDTO(session=session)
    new_match = dto.new(**user_input)
    dto.save(new_match)

    dto.insert_questions(new_match, questions)
    session.refresh(new_match)
    return new_match


@router.put("/edit/{uid}", response_model=response.Match)
def edit_match(
    uid: int,
    user_input: syntax.MatchEdit,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    match_in = user_input.dict()
    _initial_fields = match_in.pop("_initial_fields")
    match = LogicValidation(ValidateEditMatch).validate(
        match_uid=uid, match_in=match_in, db_session=session
    )
    fields_to_update = {f: v for f, v in match_in.items() if f in _initial_fields}
    dto = MatchDTO(session=session)
    dto.update(match, **fields_to_update)
    return match


@router.post("/yaml_import", response_model=response.Match)
def match_yaml_import(
    user_input: syntax.MatchYamlImport,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    user_input = user_input.dict()
    match_uid = user_input.get("uid")
    game_uid = user_input.get("game_uid")
    match = LogicValidation(ValidateMatchImport).validate(
        match_uid=match_uid, db_session=session, game_uid=game_uid
    )
    dto = MatchDTO(session=session)
    dto.insert_questions(match, user_input["data"]["questions"], game_uid)
    return match


@router.post("/import_questions", response_model=response.Match)
def import_questions(
    user_input: syntax.ImportQuestions,
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    user_input = user_input.dict()
    match_uid = user_input.get("uid")
    match = LogicValidation(ValidateMatchImport).validate(
        match_uid=match_uid, db_session=session
    )
    dto = MatchDTO(session=session)
    dto.import_template_questions(
        match, user_input["questions"], game_uid=user_input["game_uid"]
    )
    return match
