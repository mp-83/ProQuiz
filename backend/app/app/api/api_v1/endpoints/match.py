import logging

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.security import login_required
from app.domain_entities import Answer, Game, Match, Matches, Question
from app.domain_entities.db.session import get_db
from app.exceptions import NotFoundObjectError, ValidateError
from app.validation import schemas
from app.validation.logical import (
    RetrieveObject,
    ValidateEditMatch,
    ValidateMatchImport,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def list_matches(session: Session = Depends(get_db)):
    # TODO: to fix the filtering parameters
    all_matches = Matches(db_session=session).all_matches(**{})
    return {"matches": [m.json for m in all_matches]}


@router.get("/{uid}", response_model=schemas.Match)
def get_match(
    uid: int,
    session: Session = Depends(get_db),
):
    try:
        match = RetrieveObject(uid=uid, otype="match", db_session=session).get()
    except NotFoundObjectError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    return match


@router.post("/new", response_model=schemas.Match)
def create_match(
    user_input: schemas.MatchCreate,
    session: Session = Depends(get_db),
):
    user_input = user_input.dict()
    questions = user_input.pop("questions", None) or []
    new_match = Match(db_session=session, **user_input).save()
    new_game = Game(db_session=session, match_uid=new_match.uid).save()
    for position, question in enumerate(questions):
        new = Question(
            db_session=session,
            game_uid=new_game.uid,
            text=question["text"],
            position=position,
        ).save()
        for p, _answer in enumerate(question.get("answers") or []):
            session.add(
                Answer(
                    question_uid=new.uid,
                    text=_answer["text"],
                    position=p,
                    is_correct=position == 0,
                    db_session=session,
                )
            )

    session.commit()
    session.refresh(new_match)
    return new_match


@login_required
@router.put("/edit/{uid}", response_model=schemas.Match)
def edit_match(
    uid: int,
    user_input: schemas.MatchEdit,
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
    match.update(session, **user_input)
    return match


@login_required
@router.post("/yaml_import", response_model=schemas.Match)
def match_yaml_import(
    user_input: schemas.MatchYamlImport,
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

    match.insert_questions(user_input["data"]["questions"], session=session)
    return match
