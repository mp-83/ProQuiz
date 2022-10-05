import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.domain_entities.db.session import get_db
from app.domain_service.data_transfer.user import UserDTO
from app.domain_service.play import PlayerStatus, PlayScore, SinglePlayer
from app.domain_service.schemas import response
from app.domain_service.schemas import syntax_validation as syntax
from app.domain_service.schemas.logical_validation import (
    LogicValidation,
    ValidatePlayCode,
    ValidatePlayLand,
    ValidatePlayNext,
    ValidatePlaySign,
    ValidatePlayStart,
)
from app.exceptions import InternalException, MatchOver

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/h/{match_uhash}", response_model=response.UIDSchemaBase)
def land(
    match_uhash: str,
    session: Session = Depends(get_db),
):
    try:
        match_uhash = syntax.LandPlay(match_uhash=match_uhash).dict()["match_uhash"]
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    data = LogicValidation(ValidatePlayLand).validate(
        match_uhash=match_uhash, db_session=session
    )
    match = data.get("match")
    return JSONResponse(content={"match_uid": match.uid})


@router.post("/code", response_model=response.UIDSchemaBase)
def code(user_input: syntax.CodePlay, session: Session = Depends(get_db)):
    match_code = user_input.dict()["match_code"]
    data = LogicValidation(ValidatePlayCode).validate(
        match_code=match_code, db_session=session
    )
    match = data.get("match")
    user = UserDTO(session=session).fetch(signed=True)
    return JSONResponse(content={"match_uid": match.uid, "user": user.uid})


@router.post("/start", response_model=response.StartResponse)
def start(user_input: syntax.StartPlay, session: Session = Depends(get_db)):
    user_input = user_input.dict()
    data = LogicValidation(ValidatePlayStart).validate(db_session=session, **user_input)
    match = data.get("match")
    user = data.get("user")
    if not user:
        user = UserDTO(session=session).fetch(signed=match.is_restricted)

    player_status = PlayerStatus(user, match, db_session=session)
    try:
        player = SinglePlayer(player_status, user, match, db_session=session)
        current_question = player.start()
    except InternalException as exc:
        logger.error(exc.message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc

    return {
        "match_uid": match.uid,
        "question": current_question,
        "user_uid": user.uid,
    }


@router.post("/next", response_model=response.NextResponse)
def next(user_input: syntax.NextPlay, session: Session = Depends(get_db)):
    user_input = user_input.dict()
    data = LogicValidation(ValidatePlayNext).validate(db_session=session, **user_input)
    match = data.get("match")
    user = data.get("user")
    answer = data.get("answer")
    question = data.get("question")

    player_status = PlayerStatus(user, match, db_session=session)
    try:
        player = SinglePlayer(player_status, user, match, db_session=session)
    except InternalException as exc:
        logger.error(exc.message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc

    try:
        next_q = player.react(answer, question)
    except MatchOver:
        score = PlayScore(
            match.uid, user.uid, player_status.current_score(), db_session=session
        ).save_to_ranking()
        return {"question": None, "score": score.score}

    return {"question": next_q, "user_uid": user.uid, "match_uid": match.uid}


@router.post("/sign", response_model=response.SignResponse)
def sign(user_input: syntax.SignPlay, session: Session = Depends(get_db)):
    user_input = user_input.dict()
    data = LogicValidation(ValidatePlaySign).validate(db_session=session, **user_input)
    user = data.get("user")
    return {"user": user.uid}
