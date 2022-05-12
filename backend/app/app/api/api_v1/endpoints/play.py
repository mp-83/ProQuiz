import logging

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.domain_entities.db.session import get_db
from app.domain_entities.user import UserFactory
from app.domain_service.play import PlayerStatus, PlayScore, SinglePlayer
from app.domain_service.validation import syntax
from app.domain_service.validation.logical import (
    ValidatePlayCode,
    ValidatePlayLand,
    ValidatePlayNext,
    ValidatePlaySign,
    ValidatePlayStart,
)
from app.exceptions import (
    InternalException,
    MatchOver,
    NotFoundObjectError,
    ValidateError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/h/{match_uhash}", response_model=syntax.PlaySchemaBase)
def land(
    match_uhash: str,
    session: Session = Depends(get_db),
):
    try:
        match_uhash = syntax.LandPlay(match_uhash=match_uhash).dict()["match_uhash"]
    except ValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": e.errors()},
        )

    try:
        data = ValidatePlayLand(match_uhash=match_uhash, db_session=session).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": e.message}
        )

    match = data.get("match")
    return JSONResponse(content={"match": match.uid})


@router.post("/code", response_model=syntax.PlaySchemaBase)
def code(user_input: syntax.CodePlay, session: Session = Depends(get_db)):
    match_code = user_input.dict()["match_code"]
    try:
        data = ValidatePlayCode(match_code=match_code, db_session=session).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=404)
        return JSONResponse(status_code=400, content={"error": e.message})

    match = data.get("match")
    user = UserFactory(signed=True, db_session=session).fetch()
    return JSONResponse(content={"match": match.uid, "user": user.uid})


@router.post("/start")
def start(user_input: syntax.StartPlay, session: Session = Depends(get_db)):
    user_input = user_input.dict()
    try:
        data = ValidatePlayStart(db_session=session, **user_input).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=404)
        return JSONResponse(status_code=400, content={"error": e.message})

    match = data.get("match")
    user = data.get("user")
    if not user:
        user = UserFactory(signed=match.is_restricted, db_session=session).fetch()

    status = PlayerStatus(user, match, db_session=session)
    try:
        player = SinglePlayer(status, user, match, db_session=session)
        current_question = player.start()
    except InternalException as e:
        return JSONResponse(status_code=400, content={"error": e.message})

    match_data = {
        "match": match.uid,
        "question": current_question.json,
        "user": user.uid,
    }
    return JSONResponse(content=match_data)


@router.post("/next")
def next(user_input: syntax.NextPlay, session: Session = Depends(get_db)):
    user_input = user_input.dict()
    try:
        data = ValidatePlayNext(db_session=session, **user_input).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=404)
        return JSONResponse(status_code=400, content={"error": e.message})

    match = data.get("match")
    user = data.get("user")
    answer = data.get("answer")

    status = PlayerStatus(user, match, db_session=session)
    try:
        player = SinglePlayer(status, user, match, db_session=session)
    except InternalException as e:
        return JSONResponse(status_code=400, content={"error": e.message})

    try:
        next_q = player.react(answer)
    except MatchOver:
        PlayScore(
            match.uid, user.uid, status.current_score(), db_session=session
        ).save_to_ranking()
        return JSONResponse(content={"question": None})

    return JSONResponse(content={"question": next_q.json, "user": user.uid})


@router.post("/sign")
def sign(user_input: syntax.SignPlay, session: Session = Depends(get_db)):
    try:
        user_input = user_input.dict()
        data = ValidatePlaySign(db_session=session, **user_input).is_valid()
    except (NotFoundObjectError, ValidateError) as e:
        if isinstance(e, NotFoundObjectError):
            return Response(status_code=404)
        return JSONResponse(status_code=400, content={"error": e.message})

    user = data.get("user")
    return JSONResponse(content={"user": user.uid})
